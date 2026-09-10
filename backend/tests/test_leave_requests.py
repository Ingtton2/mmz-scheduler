"""연차 신청 API 테스트 (기간 단위)."""

from fastapi.testclient import TestClient


def _make_staff(client: TestClient, name: str) -> int:
    return client.post(
        "/api/staff",
        json={
            "name": name,
            "employment_type": "full_time",
            "position": "both",
            "role": "staff",
        },
    ).json()["id"]


def test_single_day_request(client: TestClient):
    sid = _make_staff(client, "하루연차")
    res = client.post(
        "/api/leave-requests",
        json={"staff_id": sid, "start_date": "2026-10-15", "end_date": "2026-10-15"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["start_date"] == "2026-10-15"
    assert body["end_date"] == "2026-10-15"
    assert body["days"] == 1


def test_range_request_and_confirm_delete(client: TestClient):
    sid = _make_staff(client, "기간연차")
    res = client.post(
        "/api/leave-requests",
        json={
            "staff_id": sid,
            "start_date": "2026-10-10",
            "end_date": "2026-10-14",
            "note": "가족 여행",
        },
    )
    assert res.status_code == 201, res.text
    req = res.json()
    assert req["days"] == 5

    res = client.patch(f"/api/leave-requests/{req['id']}", json={"status": "confirmed"})
    assert res.json()["status"] == "confirmed"

    assert client.delete(f"/api/leave-requests/{req['id']}").status_code == 204


def test_end_before_start_rejected(client: TestClient):
    sid = _make_staff(client, "역순")
    res = client.post(
        "/api/leave-requests",
        json={"staff_id": sid, "start_date": "2026-10-20", "end_date": "2026-10-18"},
    )
    assert res.status_code == 422


def test_overlapping_range_rejected(client: TestClient):
    sid = _make_staff(client, "겹침연차")
    assert (
        client.post(
            "/api/leave-requests",
            json={"staff_id": sid, "start_date": "2026-11-01", "end_date": "2026-11-05"},
        ).status_code
        == 201
    )
    # 3~7 은 1~5 와 겹침
    res = client.post(
        "/api/leave-requests",
        json={"staff_id": sid, "start_date": "2026-11-03", "end_date": "2026-11-07"},
    )
    assert res.status_code == 409
    # 6~8 은 안 겹침 -> OK
    assert (
        client.post(
            "/api/leave-requests",
            json={"staff_id": sid, "start_date": "2026-11-06", "end_date": "2026-11-08"},
        ).status_code
        == 201
    )


def test_request_for_unknown_staff_404(client: TestClient):
    res = client.post(
        "/api/leave-requests",
        json={"staff_id": 999999, "start_date": "2026-12-01", "end_date": "2026-12-01"},
    )
    assert res.status_code == 404
