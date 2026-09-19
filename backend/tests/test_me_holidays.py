"""직원용 공휴일 조회 (달력 표시용) — 로그인한 직원만, 관리자가 등록한 값 그대로."""

from fastapi.testclient import TestClient

from tests.test_me import _auth, _signup_and_approve


def test_my_holidays_requires_staff_token(client: TestClient):
    assert client.get("/api/me/holidays").status_code == 401


def test_my_holidays_returns_registered_dates_sorted(client: TestClient):
    _, token = _signup_and_approve(client, "공휴일조회")
    client.post("/api/holidays", json={"date": "2026-10-09", "name": "한글날"})
    client.post("/api/holidays", json={"date": "2026-10-03", "name": "개천절"})

    res = client.get("/api/me/holidays", headers=_auth(token))
    assert res.status_code == 200
    rows = [(h["date"], h["name"]) for h in res.json()]
    assert rows == [("2026-10-03", "개천절"), ("2026-10-09", "한글날")]
