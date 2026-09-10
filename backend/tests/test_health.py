"""가장 기본 테스트: 서버가 켜지고 /health 가 응답하는지."""

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
