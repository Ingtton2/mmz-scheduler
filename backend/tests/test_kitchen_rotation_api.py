"""주방 로테이션 미리보기/저장 API + 자동배치 연동 테스트."""

from datetime import date

from fastapi.testclient import TestClient

from app.scheduler.engine import CODE_BC, CODE_BM, CODE_BO


def _mk(client: TestClient, name: str, position: str, role: str = "staff", **extra) -> int:
    body = {"name": name, "position": position, "role": role, "employment_type": "full_time"}
    body.update(extra)
    res = client.post("/api/staff", json=body)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _setup_rotation_team(client: TestClient) -> dict[str, int]:
    ids = {
        "홀A": _mk(client, "홀A", "hall"),
        "재훈": _mk(client, "재훈", "both"),
        "희명": _mk(client, "희명", "kitchen", kitchen_rotation=True),
        "도경": _mk(client, "도경", "kitchen", kitchen_rotation=True),
        "용상": _mk(client, "용상", "kitchen", kitchen_rotation=True),
        "현석": _mk(client, "현석", "kitchen", close_backup=True),
        "주민": _mk(client, "주민", "both", role="manager"),
        "사장": _mk(client, "사장", "both", role="owner", employment_type=None),
    }
    items = []
    for wd in range(7):
        items += [
            {"weekday": wd, "position": "hall", "time_slot": "open", "min_headcount": 1},
            {"weekday": wd, "position": "hall", "time_slot": "close", "min_headcount": 1},
            {"weekday": wd, "position": "kitchen", "time_slot": "open", "min_headcount": 1},
            {"weekday": wd, "position": "kitchen", "time_slot": "mid", "min_headcount": 1},
            {"weekday": wd, "position": "kitchen", "time_slot": "close", "min_headcount": 2},
        ]
    assert client.put("/api/staffing-requirements", json={"items": items}).status_code == 200
    return ids


def test_preview_bootstraps_three_distinct_slots_when_no_prior_month(client: TestClient):
    ids = _setup_rotation_team(client)
    res = client.get("/api/kitchen-rotation", params={"year": 2026, "month": 10})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["saved"] is False

    by_name = {item["staff_name"]: item["position"] for item in body["items"]}
    assert set(by_name) == {"희명", "도경", "용상"}
    assert set(by_name.values()) == {"open", "mid", "close"}


def test_put_override_is_reflected_in_next_preview(client: TestClient):
    ids = _setup_rotation_team(client)
    preview = client.get("/api/kitchen-rotation", params={"year": 2026, "month": 10}).json()
    items = preview["items"]

    override = [
        {"staff_id": ids["희명"], "position": "open"},
        {"staff_id": ids["도경"], "position": "close"},
        {"staff_id": ids["용상"], "position": "mid"},
    ]
    put_res = client.put(
        "/api/kitchen-rotation", json={"year": 2026, "month": 10, "items": override}
    )
    assert put_res.status_code == 200, put_res.text
    assert put_res.json()["saved"] is True

    again = client.get("/api/kitchen-rotation", params={"year": 2026, "month": 10}).json()
    assert again["saved"] is True
    by_name = {item["staff_name"]: item["position"] for item in again["items"]}
    assert by_name["희명"] == "open"
    assert by_name["도경"] == "close"
    assert by_name["용상"] == "mid"


def test_rotation_shifts_one_step_in_following_month(client: TestClient):
    ids = _setup_rotation_team(client)
    fixed = [
        {"staff_id": ids["희명"], "position": "open"},
        {"staff_id": ids["도경"], "position": "mid"},
        {"staff_id": ids["용상"], "position": "close"},
    ]
    client.put("/api/kitchen-rotation", json={"year": 2026, "month": 9, "items": fixed})

    nxt = client.get("/api/kitchen-rotation", params={"year": 2026, "month": 10}).json()
    by_name = {item["staff_name"]: item["position"] for item in nxt["items"]}
    assert by_name["희명"] == "mid"
    assert by_name["도경"] == "close"
    assert by_name["용상"] == "open"


def test_auto_schedule_uses_saved_rotation_override(client: TestClient, monkeypatch):
    import app.api.routes_schedule as routes_schedule

    monkeypatch.setattr(routes_schedule, "_today", lambda: date(2026, 9, 10))
    ids = _setup_rotation_team(client)

    override = [
        {"staff_id": ids["희명"], "position": "open"},
        {"staff_id": ids["도경"], "position": "close"},
        {"staff_id": ids["용상"], "position": "mid"},
    ]
    client.put("/api/kitchen-rotation", json={"year": 2026, "month": 10, "items": override})

    res = client.post("/api/schedule/auto", json={"year": 2026, "month": 10})
    assert res.status_code == 200, res.text
    body = res.json()

    rows_by_name = {r["staff_name"]: r for r in body["rows"]}
    slot_code = {"open": CODE_BO, "mid": CODE_BM, "close": CODE_BC}
    expect = {"희명": "open", "도경": "close", "용상": "mid"}
    for name, pref in expect.items():
        cells = rows_by_name[name]["cells"]
        worked = [c for c in cells.values() if c in (CODE_BO, CODE_BM, CODE_BC)]
        assert worked, name
        assert all(c == slot_code[pref] for c in worked), (name, worked)
