"""수동 수정 + 공유(QR) + 직원 조회 API 테스트 (스펙 6.1, 6.2, 7)."""

from fastapi.testclient import TestClient


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


def test_share_and_public_view(client: TestClient):
    _setup(client)
    res = client.post("/api/schedule/2026/10/share")
    assert res.status_code == 200, res.text
    share = res.json()
    code = share["share_code"]
    assert code and share["url"].endswith(code)

    # 같은 스케줄 다시 공유 -> 같은 코드
    assert client.post("/api/schedule/2026/10/share").json()["share_code"] == code

    # QR PNG
    qr = client.get(f"/api/schedule/share/{code}/qr")
    assert qr.status_code == 200
    assert qr.headers["content-type"] == "image/png"
    assert qr.content[:8] == b"\x89PNG\r\n\x1a\n"

    # 직원 조회 (로그인 없음)
    pub = client.get(f"/api/public/schedule/{code}")
    assert pub.status_code == 200
    pj = pub.json()
    assert pj["year"] == 2026 and pj["month"] == 10
    assert len(pj["days"]) == 31
    assert len(pj["rows"]) == 4
    assert "cells" in pj["rows"][0]


def test_public_unknown_code_404(client: TestClient):
    assert client.get("/api/public/schedule/nope").status_code == 404
