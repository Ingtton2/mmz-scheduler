"""연차 = 사장님이 부여 -> 자동배치 때 직원별 사용 개수 지정 -> 자동배치가 날짜 랜덤 배정."""

from datetime import date

from fastapi.testclient import TestClient

CODE_LEAVE = "연차"


def _mk(client: TestClient, name: str, position: str = "hall", **extra) -> int:
    body = {
        "name": name,
        "position": position,
        "role": "staff",
        "employment_type": "full_time",
        "leave": {"base_off_days": 8},
    }
    body.update(extra)
    res = client.post("/api/staff", json=body)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _team(client: TestClient) -> dict[str, int]:
    ids = {n: _mk(client, n, p) for n, p in (
        ("홀A", "hall"), ("홀B", "hall"), ("겸직A", "both"), ("겸직B", "both"),
        ("주1", "kitchen"), ("주2", "kitchen"), ("주3", "kitchen"), ("주4", "kitchen"),
    )}
    ids["파트"] = client.post(
        "/api/staff",
        json={"name": "파트", "position": "hall", "role": "staff", "employment_type": "part_time"},
    ).json()["id"]
    items = []
    for wd in range(7):
        items += [
            {"weekday": wd, "position": "hall", "time_slot": "open", "min_headcount": 1},
            {"weekday": wd, "position": "hall", "time_slot": "close", "min_headcount": 1},
            {"weekday": wd, "position": "kitchen", "time_slot": "open", "min_headcount": 1},
            {"weekday": wd, "position": "kitchen", "time_slot": "close", "min_headcount": 1},
        ]
    assert client.put("/api/staffing-requirements", json={"items": items}).status_code == 200
    return ids


def _run(client: TestClient, leave_days: dict[int, int]):
    return client.post("/api/schedule/auto", json={"year": 2026, "month": 10, "leave_days": leave_days})


def _staff(client: TestClient, sid: int) -> dict:
    return next(s for s in client.get("/api/staff").json() if s["id"] == sid)


def _leave_cells(body: dict, sid: int) -> list[str]:
    row = next(r for r in body["rows"] if r["staff_id"] == sid)
    return sorted(d for d, c in row["cells"].items() if c == CODE_LEAVE)


def _setup(client: TestClient, monkeypatch) -> dict[str, int]:
    import app.api.routes_schedule as routes_schedule

    monkeypatch.setattr(routes_schedule, "_today", lambda: date(2026, 9, 10))
    ids = _team(client)
    client.post("/api/leave/grants", json={"staff_id": ids["주1"], "days": 5})
    return ids


def test_run_places_requested_leave_and_deducts_balance(client: TestClient, monkeypatch):
    ids = _setup(client, monkeypatch)
    res = _run(client, {ids["주1"]: 3})
    assert res.status_code == 200, res.text
    assert len(_leave_cells(res.json(), ids["주1"])) == 3

    s = _staff(client, ids["주1"])
    assert s["leave"]["used"] == 3 and s["leave"]["remaining"] == 2


def test_rerun_same_month_does_not_double_deduct(client: TestClient, monkeypatch):
    ids = _setup(client, monkeypatch)
    _run(client, {ids["주1"]: 3})
    second = _run(client, {ids["주1"]: 2})
    assert second.status_code == 200, second.text
    assert len(_leave_cells(second.json(), ids["주1"])) == 2
    assert _staff(client, ids["주1"])["leave"]["used"] == 2  # 5가 아니라 2

    third = _run(client, {})  # 개수를 0으로 두고 다시 -> 전부 되돌려짐
    assert _leave_cells(third.json(), ids["주1"]) == []
    assert _staff(client, ids["주1"])["leave"]["used"] == 0


def test_more_than_remaining_rejected(client: TestClient, monkeypatch):
    ids = _setup(client, monkeypatch)
    res = _run(client, {ids["주1"]: 6})
    assert res.status_code == 422
    assert "잔여연차" in res.json()["detail"]
    assert _staff(client, ids["주1"])["leave"]["used"] == 0


def test_part_time_and_unknown_staff_rejected(client: TestClient, monkeypatch):
    ids = _setup(client, monkeypatch)
    assert _run(client, {ids["파트"]: 1}).status_code == 422
    assert _run(client, {99999: 1}).status_code == 422
    assert _run(client, {ids["주1"]: -1}).status_code == 422


def test_leave_plan_endpoint_and_usage_log(client: TestClient, monkeypatch):
    ids = _setup(client, monkeypatch)
    _run(client, {ids["주1"]: 2})

    plan = client.get("/api/schedule/leave-plan", params={"year": 2026, "month": 10}).json()
    names = {p["staff_name"] for p in plan}
    assert "파트" not in names and "주1" in names
    row = next(p for p in plan if p["staff_id"] == ids["주1"])
    assert row["saved_days"] == 2
    assert row["remaining"] == 3  # 실제 잔여 (연차 사용 현황과 같은 값)
    assert row["max_days"] == 5  # 이 달에 이미 차감된 2개는 다시 돌릴 때 되돌려지므로 지정 가능 최대치에 포함

    usage = client.get("/api/leave/usage-log").json()
    u = next(x for x in usage if x["staff_id"] == ids["주1"])
    assert u["days"] == 2 and u["remaining_after"] == 3
    assert u["year_month"] == "2026-10" and len(u["dates"]) == 2


# --- 표에서 수기로 연차 칸을 바꾸는 경우 ---


def _edit(client: TestClient, sid: int, day: str, code: str):
    return client.patch(
        "/api/schedule/entries",
        json={"year": 2026, "month": 10, "changes": [{"staff_id": sid, "work_date": day, "work_code": code}]},
    )


def test_manual_leave_cell_deducts_and_refunds_balance(client: TestClient, monkeypatch):
    ids = _setup(client, monkeypatch)
    _run(client, {})  # 연차 없이 배치만
    sid = ids["주1"]

    assert _edit(client, sid, "2026-10-14", "연차").status_code == 200
    s = _staff(client, sid)
    assert s["leave"]["used"] == 1 and s["leave"]["remaining"] == 4

    # 같은 칸을 다시 "연차"로 저장해도 중복 차감되지 않음
    _edit(client, sid, "2026-10-14", "연차")
    assert _staff(client, sid)["leave"]["used"] == 1

    # 연차를 다른 코드로 되돌리면 환급
    assert _edit(client, sid, "2026-10-14", "D/O").status_code == 200
    assert _staff(client, sid)["leave"]["used"] == 0


def test_manual_leave_rejected_when_balance_short(client: TestClient, monkeypatch):
    ids = _setup(client, monkeypatch)
    _run(client, {})
    res = _edit(client, ids["주2"], "2026-10-14", "연차")  # 주2는 부여연차 0
    assert res.status_code == 422
    assert "잔여연차" in res.json()["detail"]
    assert _staff(client, ids["주2"])["leave"]["used"] == 0


def test_manual_leave_shows_in_usage_log(client: TestClient, monkeypatch):
    ids = _setup(client, monkeypatch)
    _run(client, {})
    _edit(client, ids["주1"], "2026-10-14", "연차")
    u = next(x for x in client.get("/api/leave/usage-log").json() if x["staff_id"] == ids["주1"])
    assert u["days"] == 1 and u["dates"] == ["2026-10-14"] and u["remaining_after"] == 4
