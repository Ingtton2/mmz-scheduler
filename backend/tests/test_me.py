"""직원 셀프서비스 "내 정보" API 테스트 (스펙 9-4, 9-5)."""

from datetime import date

import app.api.routes_me as routes_me
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


def test_leave_request_window_enforced(client: TestClient, monkeypatch):
    _, token = _signup_and_approve(client, "연차셀프")
    # 오늘을 2026-09-10 으로 고정 -> 10월만 허용, 20일 이전이라 열려 있음
    monkeypatch.setattr(routes_me, "_today", lambda: date(2026, 9, 10))

    ok = client.post(
        "/api/me/leave-requests",
        json={"start_date": "2026-10-05", "end_date": "2026-10-05"},
        headers=_auth(token),
    )
    assert ok.status_code == 201

    wrong_month = client.post(
        "/api/me/leave-requests",
        json={"start_date": "2026-11-05", "end_date": "2026-11-05"},
        headers=_auth(token),
    )
    assert wrong_month.status_code == 422

    # 겹치는 기간은 거부
    dup = client.post(
        "/api/me/leave-requests",
        json={"start_date": "2026-10-05", "end_date": "2026-10-06"},
        headers=_auth(token),
    )
    assert dup.status_code == 409

    listed = client.get("/api/me/leave-requests", headers=_auth(token)).json()
    assert len(listed) == 1
    assert listed[0]["start_date"] == "2026-10-05"


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


def test_part_time_blocked_from_leave_and_dayoff(client: TestClient, monkeypatch):
    _, token = _signup_and_approve(
        client, "파트타임셀프", employment_type="part_time"
    )
    monkeypatch.setattr(routes_me, "_today", lambda: date(2026, 9, 10))

    leave = client.post(
        "/api/me/leave-requests",
        json={"start_date": "2026-10-05", "end_date": "2026-10-05"},
        headers=_auth(token),
    )
    assert leave.status_code == 400

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


def test_my_schedule_returns_only_own_cells(client: TestClient):
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

    res = client.get("/api/me/schedule/2026/10", headers=_auth(a_token))
    assert res.status_code == 200
    body = res.json()
    # 본인(A)의 10/1 은 수정한 대로 FO, B 의 값(FC)은 섞여 나오지 않아야 함
    assert body["cells"]["2026-10-01"] == "FO"
    assert all(code != "FC" for code in body["cells"].values())
    assert body["summary"]["hall"] >= 1
