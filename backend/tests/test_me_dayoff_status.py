"""직원 "사전 휴무 신청" 목록에 승인 상태(신청/확정/반려)가 내려가는지."""

from datetime import date

from fastapi.testclient import TestClient

import app.api.routes_me as routes_me
from tests.test_me import _auth, _signup_and_approve


def test_my_dayoff_status_follows_admin_approval(client: TestClient, monkeypatch):
    _, token = _signup_and_approve(client, "사휴상태")
    monkeypatch.setattr(routes_me, "_today", lambda: date(2026, 9, 10))

    created = client.post(
        "/api/me/dayoff-requests",
        json={"start_date": "2026-10-05", "end_date": "2026-10-05"},
        headers=_auth(token),
    )
    assert created.status_code == 201
    assert created.json()["status"] == "requested"
    req_id = created.json()["id"]

    def my_status() -> str:
        rows = client.get("/api/me/dayoff-requests", headers=_auth(token)).json()
        return next(r["status"] for r in rows if r["id"] == req_id)

    assert my_status() == "requested"

    client.patch(f"/api/dayoff-requests/{req_id}", json={"status": "confirmed"})
    assert my_status() == "confirmed"

    client.patch(f"/api/dayoff-requests/{req_id}", json={"status": "rejected"})
    assert my_status() == "rejected"
