"""수동 수정 + 공유(직원 로그인 후 조회) API 테스트 (스펙 6.1, 6.2, 7)."""

from datetime import date

import app.api.routes_me as routes_me
import app.api.routes_schedule as routes_schedule
import pytest
from fastapi.testclient import TestClient

# 이 파일의 모든 테스트가 2026년 10월을 "다음 달"로 쓰므로, 실제 시계가
# 2026-10 을 지나도 자동배치 시점 제한(당월 이후 금지)에 안 걸리게
# "오늘"을 9월로 고정한다.
@pytest.fixture(autouse=True)
def _fixed_today(monkeypatch):
    monkeypatch.setattr(routes_schedule, "_today", lambda: date(2026, 9, 10))
    monkeypatch.setattr(routes_me, "_today", lambda: date(2026, 9, 10))


def _setup(client: TestClient) -> None:
    for nm, pos in [("홀A", "hall"), ("겸A", "both"), ("주1", "kitchen"), ("주2", "kitchen")]:
        client.post(
            "/api/staff",
            json={"name": nm, "employment_type": "full_time", "position": pos, "role": "staff"},
        )
    items = []
    for wd in range(7):
        items += [
            {"weekday": wd, "position": "hall", "time_slot": "open", "min_headcount": 1},
            {"weekday": wd, "position": "hall", "time_slot": "close", "min_headcount": 1},
            {"weekday": wd, "position": "kitchen", "time_slot": "open", "min_headcount": 1},
            {"weekday": wd, "position": "kitchen", "time_slot": "close", "min_headcount": 1},
        ]
    client.put("/api/staffing-requirements", json={"items": items})
    assert client.post("/api/schedule/auto", json={"year": 2026, "month": 10}).status_code == 200


def _signup_and_approve(client: TestClient, name: str) -> str:
    sid = client.post(
        "/api/staff",
        json={"name": name, "employment_type": "full_time", "position": "hall", "role": "staff"},
    ).json()["id"]
    client.post("/api/public/staff-accounts/signup", json={"staff_id": sid, "pin": "1234"})
    pending = client.get("/api/staff-accounts/pending").json()
    account_id = next(p["account_id"] for p in pending if p["staff_id"] == sid)
    client.post(f"/api/staff-accounts/{account_id}/approve")
    token = client.post(
        "/api/public/staff-accounts/login", json={"staff_id": sid, "pin": "1234"}
    ).json()["token"]
    return token


def test_manual_edit_changes_cell(client: TestClient):
    _setup(client)
    body = client.get("/api/schedule", params={"year": 2026, "month": 10}).json()
    row = body["rows"][0]
    sid = row["staff_id"]
    day = body["days"][10]

    res = client.patch(
        "/api/schedule/entries",
        json={
            "year": 2026,
            "month": 10,
            "changes": [{"staff_id": sid, "work_date": day, "work_code": "연차"}],
        },
    )
    assert res.status_code == 200, res.text
    out = res.json()
    assert out["edited"] is True
    changed = next(r for r in out["rows"] if r["staff_id"] == sid)
    assert changed["cells"][day] == "연차"
    # 요약도 재계산됨
    assert changed["summary"]["leave"] >= 1


def test_manual_edit_rejects_bad_code(client: TestClient):
    _setup(client)
    body = client.get("/api/schedule", params={"year": 2026, "month": 10}).json()
    res = client.patch(
        "/api/schedule/entries",
        json={
            "year": 2026,
            "month": 10,
            "changes": [
                {"staff_id": body["rows"][0]["staff_id"], "work_date": body["days"][0], "work_code": "XX"}
            ],
        },
    )
    assert res.status_code == 422


def test_manual_edit_no_schedule_404(client: TestClient):
    res = client.patch(
        "/api/schedule/entries",
        json={"year": 2099, "month": 1, "changes": []},
    )
    assert res.status_code == 404


def test_share_sets_confirmed_and_reuses_code(client: TestClient):
    _setup(client)
    res = client.post("/api/schedule/2026/10/share")
    assert res.status_code == 200, res.text
    code = res.json()["share_code"]
    assert code

    assert client.get("/api/schedule", params={"year": 2026, "month": 10}).json()["status"] == "confirmed"

    # 같은 스케줄 다시 공유 -> 같은 코드 (직원 로그인 화면 데이터 식별용으로만 쓰임)
    assert client.post("/api/schedule/2026/10/share").json()["share_code"] == code


def test_share_records_and_refreshes_published_at(client: TestClient):
    _setup(client)
    assert client.get("/api/schedule", params={"year": 2026, "month": 10}).json()["published_at"] is None

    first = client.post("/api/schedule/2026/10/share").json()["published_at"]
    assert first is not None
    assert client.get("/api/schedule", params={"year": 2026, "month": 10}).json()["published_at"] == first

    # 재공유하면 최신 시각으로 갱신된다.
    second = client.post("/api/schedule/2026/10/share").json()["published_at"]
    assert second is not None
    assert second >= first


def test_draft_hidden_until_shared(client: TestClient):
    """자동배치 직후(공유 전)엔 상태가 draft 이고, 로그인한 직원에게도 안 보인다."""
    _setup(client)
    token = _signup_and_approve(client, "직원A")
    headers = {"Authorization": f"Bearer {token}"}

    saved = client.get("/api/schedule", params={"year": 2026, "month": 10}).json()
    assert saved["status"] == "draft"
    assert client.get("/api/me/team-schedule/2026/10", headers=headers).status_code == 404

    client.post("/api/schedule/2026/10/share")
    assert client.get("/api/me/team-schedule/2026/10", headers=headers).status_code == 200

    # 다시 자동배치를 돌리면 (재계산) 임시로 되돌아가야 한다.
    client.post("/api/schedule/auto", json={"year": 2026, "month": 10})
    again = client.get("/api/schedule", params={"year": 2026, "month": 10}).json()
    assert again["status"] == "draft"

    assert client.get("/api/me/team-schedule/2026/10", headers=headers).status_code == 404


def test_edit_after_share_reverts_then_reshare_reveals(client: TestClient):
    """임시 -> 공유 -> (재수정) -> 다시 임시 -> 재공유 -> 다시 노출 흐름 전체 확인."""
    _setup(client)
    token = _signup_and_approve(client, "직원B")
    headers = {"Authorization": f"Bearer {token}"}

    body = client.get("/api/schedule", params={"year": 2026, "month": 10}).json()
    sid = body["rows"][0]["staff_id"]
    staff_name = body["rows"][0]["staff_name"]
    day = body["days"][5]

    # 1) 공유 -> confirmed, 로그인한 직원에게 보임
    client.post("/api/schedule/2026/10/share")
    assert client.get("/api/schedule", params={"year": 2026, "month": 10}).json()["status"] == "confirmed"
    assert client.get("/api/me/team-schedule/2026/10", headers=headers).status_code == 200

    # 2) 공유 후 수정 -> 다시 draft, 직원 화면에서 사라짐
    edit = client.patch(
        "/api/schedule/entries",
        json={
            "year": 2026,
            "month": 10,
            "changes": [{"staff_id": sid, "work_date": day, "work_code": "연차"}],
        },
    )
    assert edit.json()["status"] == "draft"
    assert client.get("/api/me/team-schedule/2026/10", headers=headers).status_code == 404

    # 3) 재공유 -> 다시 confirmed, 다시 보임 + 수정 내용 반영
    client.post("/api/schedule/2026/10/share")
    again = client.get("/api/me/team-schedule/2026/10", headers=headers)
    assert again.status_code == 200
    changed_row = next(r for r in again.json()["rows"] if r["staff_name"] == staff_name)
    assert changed_row["cells"][day] == "연차"
