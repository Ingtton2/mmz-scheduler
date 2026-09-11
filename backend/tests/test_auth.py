"""관리자 로그인 (스펙 9 간이 버전) 테스트.

ADMIN_USER/ADMIN_PASS 가 없으면(기본값) 로그인 기능 자체가 꺼져 있어야 하고,
설정돼 있으면 토큰 없이는 관리자 API 가 막혀야 한다.
"""

from fastapi.testclient import TestClient

from app.config import settings


def test_auth_disabled_by_default(client: TestClient):
    """ADMIN_USER/ADMIN_PASS 를 설정 안 하면 로그인 없이 그대로 다 열려 있다 (로컬 개발)."""
    assert settings.admin_auth_enabled is False
    assert client.get("/api/auth/status").json() == {"enabled": False}
    assert client.get("/api/staff").status_code == 200


def test_login_blocks_admin_api_until_authenticated(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "admin_user", "boss")
    monkeypatch.setattr(settings, "admin_pass", "secret123")
    assert settings.admin_auth_enabled is True

    # 공개 경로는 그대로 열려 있어야 함.
    assert client.get("/health").status_code == 200
    assert client.get("/api/auth/status").json() == {"enabled": True}

    # 토큰 없이 관리자 API 는 막힘.
    res = client.get("/api/staff")
    assert res.status_code == 401

    # 잘못된 비밀번호는 거부.
    bad = client.post("/api/auth/login", json={"username": "boss", "password": "wrong"})
    assert bad.status_code == 401

    # 올바른 아이디/비밀번호로 로그인 → 토큰 발급.
    ok = client.post("/api/auth/login", json={"username": "boss", "password": "secret123"})
    assert ok.status_code == 200
    token = ok.json()["token"]
    assert token

    headers = {"Authorization": f"Bearer {token}"}

    # 토큰이 있으면 통과.
    assert client.get("/api/staff", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 200

    # 로그아웃하면 토큰이 즉시 무효화됨.
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/staff", headers=headers).status_code == 401
    assert client.get("/api/auth/me", headers=headers).status_code == 401
