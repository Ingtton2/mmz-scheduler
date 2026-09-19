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

    client.patch(
        f"/api/dayoff-requests/{req_id}",
        json={"status": "rejected", "reject_reason": "인원 부족"},
    )
    assert my_status() == "rejected"


def _admin_dayoff(client: TestClient, staff_id: int, **extra) -> dict:
    body = {"staff_id": staff_id, "start_date": "2026-10-06", "end_date": "2026-10-06", **extra}
    res = client.post("/api/dayoff-requests", json=body)
    assert res.status_code == 201, res.text
    return res.json()


def test_reject_requires_reason(client: TestClient):
    sid, _ = _signup_and_approve(client, "사유필수")
    req = _admin_dayoff(client, sid)

    for body in ({"status": "rejected"}, {"status": "rejected", "reject_reason": "   "}):
        res = client.patch(f"/api/dayoff-requests/{req['id']}", json=body)
        assert res.status_code == 422
        assert "반려 사유" in res.json()["detail"]

    unchanged = next(r for r in client.get("/api/dayoff-requests").json() if r["id"] == req["id"])
    assert unchanged["status"] == "requested"

    # 관리자가 직접 등록할 때 바로 반려로 넣는 경우도 사유가 필요하다
    res = client.post(
        "/api/dayoff-requests",
        json={"staff_id": sid, "start_date": "2026-10-20", "end_date": "2026-10-20", "status": "rejected"},
    )
    assert res.status_code == 422


def test_reject_reason_reaches_staff_and_clears_when_reopened(client: TestClient):
    sid, token = _signup_and_approve(client, "사유전달")
    req = _admin_dayoff(client, sid)

    def mine():
        rows = client.get("/api/me/dayoff-requests", headers=_auth(token)).json()
        return next(r for r in rows if r["id"] == req["id"])

    res = client.patch(
        f"/api/dayoff-requests/{req['id']}",
        json={"status": "rejected", "reject_reason": "  그날 인원이 부족해요  "},
    )
    assert res.status_code == 200
    assert res.json()["reject_reason"] == "그날 인원이 부족해요"
    assert mine()["status"] == "rejected"
    assert mine()["reject_reason"] == "그날 인원이 부족해요"

    client.patch(f"/api/dayoff-requests/{req['id']}", json={"status": "requested"})
    assert mine()["status"] == "requested"
    assert mine()["reject_reason"] is None

    client.patch(f"/api/dayoff-requests/{req['id']}", json={"status": "confirmed", "reject_reason": "무시됨"})
    assert mine()["reject_reason"] is None


def test_staff_can_delete_own_pending_dayoff_only(client: TestClient, monkeypatch):
    sid, token = _signup_and_approve(client, "직접삭제")
    other_id, other_token = _signup_and_approve(client, "남의것")
    monkeypatch.setattr(routes_me, "_today", lambda: date(2026, 9, 10))

    def make(tok: str, day: str) -> int:
        res = client.post(
            "/api/me/dayoff-requests",
            json={"start_date": day, "end_date": day},
            headers=_auth(tok),
        )
        assert res.status_code == 201, res.text
        return res.json()["id"]

    mine = make(token, "2026-10-05")
    theirs = make(other_token, "2026-10-06")

    # 남의 신청은 못 지운다 (있는지조차 모르게 404)
    assert client.delete(f"/api/me/dayoff-requests/{theirs}", headers=_auth(token)).status_code == 404

    # 확정된 건은 못 지운다
    client.patch(f"/api/dayoff-requests/{mine}", json={"status": "confirmed"})
    res = client.delete(f"/api/me/dayoff-requests/{mine}", headers=_auth(token))
    assert res.status_code == 400
    assert "사장님께 문의" in res.json()["detail"]

    # 다시 신청 상태가 되면 지울 수 있다
    client.patch(f"/api/dayoff-requests/{mine}", json={"status": "requested"})
    assert client.delete(f"/api/me/dayoff-requests/{mine}", headers=_auth(token)).status_code == 204
    left = [r["id"] for r in client.get("/api/me/dayoff-requests", headers=_auth(token)).json()]
    assert mine not in left


def test_staff_cannot_delete_pending_after_cutoff(client: TestClient, monkeypatch):
    _, token = _signup_and_approve(client, "마감후삭제")
    monkeypatch.setattr(routes_me, "_today", lambda: date(2026, 9, 10))
    req_id = client.post(
        "/api/me/dayoff-requests",
        json={"start_date": "2026-10-05", "end_date": "2026-10-05"},
        headers=_auth(token),
    ).json()["id"]

    monkeypatch.setattr(routes_me, "_today", lambda: date(2026, 9, 21))
    res = client.delete(f"/api/me/dayoff-requests/{req_id}", headers=_auth(token))
    assert res.status_code == 400
    assert "신청 기간" in res.json()["detail"]
