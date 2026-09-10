"""사전 휴무 신청 API 테스트 (스펙 3.1) — 기간 단위."""

from fastapi.testclient import TestClient


def _staff(client: TestClient, name: str) -> int:
    return client.post(
        "/api/staff",
        json={
            "name": name,
            "employment_type": "full_time",
            "position": "both",
            "role": "staff",
        },
    ).json()["id"]


def _post(client: TestClient, sid: int, start: str, end: str):
    return client.post(
        "/api/dayoff-requests",
        json={"staff_id": sid, "start_date": start, "end_date": end},
    )


def test_range_create_list_delete(client: TestClient):
    sid = _staff(client, "사휴기간")
    res = _post(client, sid, "2026-10-10", "2026-10-13")
    assert res.status_code == 201, res.text
    rid = res.json()["id"]
    assert res.json()["days"] == 4

    assert any(r["id"] == rid for r in client.get("/api/dayoff-requests").json())
    assert client.delete(f"/api/dayoff-requests/{rid}").status_code == 204


def test_max_per_month_range(client: TestClient):
    from app.models import MAX_PER_MONTH

    sid = _staff(client, "월한도기간")
    # 한도만큼 한 번에 신청
    assert _post(client, sid, "2026-10-01", f"2026-10-{MAX_PER_MONTH:02d}").status_code == 201
    # 같은 달 하루 더 -> 거부
    res = _post(
        client, sid, f"2026-10-{MAX_PER_MONTH + 1:02d}", f"2026-10-{MAX_PER_MONTH + 1:02d}"
    )
    assert res.status_code == 422
    assert str(MAX_PER_MONTH) in res.json()["detail"]
    # 11월은 다시 가능
    assert _post(client, sid, "2026-11-01", "2026-11-01").status_code == 201


def test_range_spanning_two_months_counts_per_month(client: TestClient):
    from app.models import MAX_PER_MONTH

    sid = _staff(client, "월경계")
    # 10월 말~11월 초 걸치는 기간: 각 달 일수가 한도 이하이면 OK
    res = _post(client, sid, "2026-10-29", "2026-11-02")
    assert res.status_code == 201, res.text
    assert res.json()["days"] == 5
    # 이후 10월에 (한도-3)일 넘게 더 신청하면 10월 초과로 거부
    res = _post(client, sid, "2026-10-01", f"2026-10-{MAX_PER_MONTH:02d}")
    assert res.status_code == 422


def test_overlap_rejected(client: TestClient):
    sid = _staff(client, "사휴겹침")
    assert _post(client, sid, "2026-10-05", "2026-10-08").status_code == 201
    assert _post(client, sid, "2026-10-07", "2026-10-10").status_code == 409
    assert _post(client, sid, "2026-10-09", "2026-10-11").status_code == 201


def test_unknown_staff_404(client: TestClient):
    res = _post(client, 999999, "2026-10-01", "2026-10-01")
    assert res.status_code == 404
