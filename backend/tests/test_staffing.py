"""포지션 x 시간대 필요 인원 설정 API 테스트."""

from fastapi.testclient import TestClient


def _grid():
    items = []
    for wd in range(7):
        items += [
            {"weekday": wd, "position": "hall", "time_slot": "open", "min_headcount": 1},
            {"weekday": wd, "position": "hall", "time_slot": "close", "min_headcount": 1},
            {"weekday": wd, "position": "kitchen", "time_slot": "open", "min_headcount": 1},
            {"weekday": wd, "position": "kitchen", "time_slot": "mid", "min_headcount": 1},
            {"weekday": wd, "position": "kitchen", "time_slot": "close", "min_headcount": 2},
        ]
    return items


def test_put_and_get(client: TestClient):
    res = client.put("/api/staffing-requirements", json={"items": _grid()})
    assert res.status_code == 200, res.text
    got = res.json()
    assert len(got) == 35  # 7요일 x 5슬롯

    res = client.get("/api/staffing-requirements")
    grid = {
        (r["weekday"], r["position"], r["time_slot"]): r["min_headcount"]
        for r in res.json()
    }
    assert grid[(0, "hall", "open")] == 1
    assert grid[(0, "kitchen", "close")] == 2
    assert (0, "hall", "mid") not in grid


def test_put_replaces(client: TestClient):
    client.put("/api/staffing-requirements", json={"items": _grid()})
    res = client.put(
        "/api/staffing-requirements",
        json={
            "items": [
                {"weekday": 1, "position": "hall", "time_slot": "open", "min_headcount": 3}
            ]
        },
    )
    assert len(res.json()) == 1


def test_bad_slot_rejected(client: TestClient):
    res = client.put(
        "/api/staffing-requirements",
        json={
            "items": [
                {"weekday": 0, "position": "hall", "time_slot": "lunch", "min_headcount": 1}
            ]
        },
    )
    assert res.status_code == 422
