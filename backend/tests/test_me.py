"""직원 셀프서비스 "내 정보" API 테스트 (스펙 9-4, 9-5)."""

from datetime import date

import app.api.routes_me as routes_me
import app.api.routes_schedule as routes_schedule
from fastapi.testclient import TestClient


def _signup_and_approve(client: TestClient, name: str, **staff_kw) -> tuple[int, str]:
    payload = {
        "name": name,
        "employment_type": staff_kw.pop("employment_type", "full_time"),
        "position": staff_kw.pop("position", "hall"),
        "role": staff_kw.pop("role", "staff"),
    }
    payload.update(staff_kw)
    if payload.get("role") == "owner":
        payload.pop("employment_type", None)
    sid = client.post("/api/staff", json=payload).json()["id"]

    client.post("/api/public/staff-accounts/signup", json={"staff_id": sid, "pin": "1234"})
    if payload["role"] != "owner":
        pending = client.get("/api/staff-accounts/pending").json()
        account_id = next(p["account_id"] for p in pending if p["staff_id"] == sid)
        client.post(f"/api/staff-accounts/{account_id}/approve")

    login = client.post("/api/public/staff-accounts/login", json={"staff_id": sid, "pin": "1234"})
    return sid, login.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_me_requires_token(client: TestClient):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers=_auth("garbage")).status_code == 401


def test_me_returns_own_info(client: TestClient):
    sid, token = _signup_and_approve(client, "본인정보")
    res = client.get("/api/me", headers=_auth(token))
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == sid
    assert body["name"] == "본인정보"
    assert body["must_change_pin"] is False


def test_change_pin_requires_current_pin(client: TestClient):
    _, token = _signup_and_approve(client, "핀변경")
    bad = client.post(
        "/api/me/change-pin",
        json={"current_pin": "0000", "new_pin": "4321"},
        headers=_auth(token),
    )
    assert bad.status_code == 401

    ok = client.post(
        "/api/me/change-pin",
        json={"current_pin": "1234", "new_pin": "4321"},
        headers=_auth(token),
    )
    assert ok.status_code == 200

    # 새 PIN 으로 재로그인 가능해야 함
    sid = client.get("/api/me", headers=_auth(token)).json()["id"]
    relogin = client.post(
        "/api/public/staff-accounts/login", json={"staff_id": sid, "pin": "4321"}
    )
    assert relogin.status_code == 200


def test_self_service_leave_request_endpoints_removed(client: TestClient):
    """연차는 직원이 날짜로 신청하지 않는다 — 신청/취소 엔드포인트가 없고 조회만 가능."""
    _, token = _signup_and_approve(client, "연차셀프")

    res = client.post(
        "/api/me/leave-requests",
        json={"start_date": "2026-10-05", "end_date": "2026-10-05"},
        headers=_auth(token),
    )
    assert res.status_code == 405
    assert client.delete("/api/me/leave-requests/1", headers=_auth(token)).status_code == 404
    assert client.get("/api/me/leave-requests", headers=_auth(token)).status_code == 200


def test_request_window_closed_after_cutoff(client: TestClient, monkeypatch):
    _, token = _signup_and_approve(client, "마감일지남")
    # 9월 21일 (20일 마감 지남) -> 셀프 신청 자체가 막혀야 함
    monkeypatch.setattr(routes_me, "_today", lambda: date(2026, 9, 21))

    res = client.post(
        "/api/me/dayoff-requests",
        json={"start_date": "2026-10-05", "end_date": "2026-10-05"},
        headers=_auth(token),
    )
    assert res.status_code == 422
    assert "20일" in res.json()["detail"]


def test_part_time_blocked_from_dayoff(client: TestClient, monkeypatch):
    _, token = _signup_and_approve(
        client, "파트타임셀프", employment_type="part_time"
    )
    monkeypatch.setattr(routes_me, "_today", lambda: date(2026, 9, 10))

    dayoff = client.post(
        "/api/me/dayoff-requests",
        json={"start_date": "2026-10-05", "end_date": "2026-10-05"},
        headers=_auth(token),
    )
    assert dayoff.status_code == 400


def test_dayoff_month_quota_enforced_for_self_service(client: TestClient, monkeypatch):
    _, token = _signup_and_approve(client, "월한도셀프")
    monkeypatch.setattr(routes_me, "_today", lambda: date(2026, 9, 1))

    big = client.post(
        "/api/me/dayoff-requests",
        json={"start_date": "2026-10-01", "end_date": "2026-10-21"},  # 21일 > 20일 한도
        headers=_auth(token),
    )
    assert big.status_code == 422


def test_my_schedule_returns_only_own_cells(client: TestClient, monkeypatch):
    monkeypatch.setattr(routes_schedule, "_today", lambda: date(2026, 9, 10))
    a_id, a_token = _signup_and_approve(client, "스케줄본인A")
    b_id, _ = _signup_and_approve(client, "스케줄본인B")

    # 스케줄이 없으면 404
    assert client.get("/api/me/schedule/2026/10", headers=_auth(a_token)).status_code == 404

    assert client.post("/api/schedule/auto", json={"year": 2026, "month": 10}).status_code == 200
    client.patch(
        "/api/schedule/entries",
        json={
            "year": 2026,
            "month": 10,
            "changes": [
                {"staff_id": a_id, "work_date": "2026-10-01", "work_code": "FO"},
                {"staff_id": b_id, "work_date": "2026-10-01", "work_code": "FC"},
            ],
        },
    )

    # 아직 공유 전(임시) 이라 본인 스케줄도 안 보여야 함.
    assert client.get("/api/me/schedule/2026/10", headers=_auth(a_token)).status_code == 404

    assert client.post("/api/schedule/2026/10/share").status_code == 200

    res = client.get("/api/me/schedule/2026/10", headers=_auth(a_token))
    assert res.status_code == 200
    body = res.json()
    # 본인(A)의 10/1 은 수정한 대로 FO, B 의 값(FC)은 섞여 나오지 않아야 함
    assert body["cells"]["2026-10-01"] == "FO"
    assert all(code != "FC" for code in body["cells"].values())
    assert body["summary"]["hall"] >= 1


def test_team_schedule_requires_shared_status(client: TestClient, monkeypatch):
    """동료 스케줄 전체 조회 — 공유되기 전엔 로그인해도 안 보여야 한다."""
    monkeypatch.setattr(routes_schedule, "_today", lambda: date(2026, 9, 10))
    monkeypatch.setattr(routes_me, "_today", lambda: date(2026, 9, 10))
    a_id, a_token = _signup_and_approve(client, "동료본인")
    b_id, _ = _signup_and_approve(client, "동료B")

    # "오늘"을 9/10 으로 고정 -> 다음 달인 10월 스케줄로 테스트.
    assert client.post("/api/schedule/auto", json={"year": 2026, "month": 10}).status_code == 200

    # 아직 공유 전 -> 로그인했어도 전체 스케줄 안 보임
    blocked = client.get("/api/me/team-schedule/2026/10", headers=_auth(a_token))
    assert blocked.status_code == 404

    client.post("/api/schedule/2026/10/share")
    ok = client.get("/api/me/team-schedule/2026/10", headers=_auth(a_token))
    assert ok.status_code == 200
    body = ok.json()
    names = [r["staff_name"] for r in body["rows"]]
    assert "동료본인" in names and "동료B" in names
