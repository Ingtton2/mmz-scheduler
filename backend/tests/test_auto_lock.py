"""월별 자동배치 잠금: 잠긴 달은 서버가 자동배치 실행을 거절한다."""

from datetime import date

from fastapi.testclient import TestClient


def _setup(client: TestClient, monkeypatch) -> None:
    import app.api.routes_schedule as routes_schedule

    monkeypatch.setattr(routes_schedule, "_today", lambda: date(2026, 9, 10))
    for nm, pos in (("홀A", "hall"), ("주1", "kitchen"), ("주2", "kitchen")):
        client.post(
            "/api/staff",
            json={"name": nm, "position": pos, "role": "staff", "employment_type": "full_time"},
        )
    items = [
        {"weekday": wd, "position": "hall", "time_slot": "open", "min_headcount": 1}
        for wd in range(7)
    ]
    client.put("/api/staffing-requirements", json={"items": items})


def _run(client: TestClient):
    return client.post("/api/schedule/auto", json={"year": 2026, "month": 10})


def _lock(client: TestClient, locked: bool):
    return client.put("/api/schedule/2026/10/auto-lock", json={"locked": locked})


def test_lock_requires_a_saved_schedule(client: TestClient, monkeypatch):
    _setup(client, monkeypatch)
    assert _lock(client, True).status_code == 404


def test_locked_month_rejects_auto_run_and_keeps_schedule(client: TestClient, monkeypatch):
    _setup(client, monkeypatch)
    first = _run(client).json()
    assert first["auto_locked"] is False

    res = _lock(client, True)
    assert res.status_code == 200 and res.json()["auto_locked"] is True
    assert client.get("/api/schedule", params={"year": 2026, "month": 10}).json()["auto_locked"] is True

    blocked = _run(client)
    assert blocked.status_code == 423
    assert "잠겨" in blocked.json()["detail"]
    saved = client.get("/api/schedule", params={"year": 2026, "month": 10}).json()
    assert [r["cells"] for r in saved["rows"]] == [r["cells"] for r in first["rows"]]


def test_unlock_allows_auto_run_again(client: TestClient, monkeypatch):
    _setup(client, monkeypatch)
    _run(client)
    _lock(client, True)
    assert _lock(client, False).json()["auto_locked"] is False
    res = _run(client)
    assert res.status_code == 200 and res.json()["auto_locked"] is False


def test_manual_edit_and_share_still_work_while_locked(client: TestClient, monkeypatch):
    import app.api.routes_me as routes_me

    monkeypatch.setattr(routes_me, "_today", lambda: date(2026, 9, 10))
    _setup(client, monkeypatch)
    body = _run(client).json()
    _lock(client, True)

    row = body["rows"][0]
    day = body["days"][0]
    res = client.patch(
        "/api/schedule/entries",
        json={"year": 2026, "month": 10, "changes": [{"staff_id": row["staff_id"], "work_date": day, "work_code": "D/O"}]},
    )
    assert res.status_code == 200 and res.json()["auto_locked"] is True
    assert client.post("/api/schedule/2026/10/share").status_code == 200
    assert client.get("/api/schedule", params={"year": 2026, "month": 10}).json()["auto_locked"] is True
