"""로그인 유지 테스트 — 토큰이 서버 메모리가 아니라 DB 에 저장되는지, 만료/연장/분리가 맞는지."""

import time

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.database import engine
from app.models import LoginSession
from app.services import auth_tokens, login_sessions, staff_tokens
from tests.test_me import _auth, _signup_and_approve


def test_token_survives_restart_because_stored_in_db():
    token = auth_tokens.issue_token()
    with Session(engine) as s:
        rows = s.exec(select(LoginSession)).all()
    assert len(rows) == 1
    assert rows[0].token_hash != token  # 원문은 저장하지 않음
    # 메모리 상태가 없으므로 "재시작" 후에도 같은 결과
    assert auth_tokens.verify_token(token) is True


def test_expired_token_rejected_and_deleted():
    token = auth_tokens.issue_token()
    with Session(engine) as s:
        row = s.exec(select(LoginSession)).one()
        row.expires_at = time.time() - 1
        s.add(row)
        s.commit()
    assert auth_tokens.verify_token(token) is False
    with Session(engine) as s:
        assert s.exec(select(LoginSession)).all() == []


def test_sliding_expiry_extends_when_used():
    token = auth_tokens.issue_token()
    with Session(engine) as s:
        row = s.exec(select(LoginSession)).one()
        row.expires_at = time.time() + 3600  # 1시간 남음 (7일의 절반 미만)
        s.add(row)
        s.commit()
    assert auth_tokens.verify_token(token) is True
    with Session(engine) as s:
        row = s.exec(select(LoginSession)).one()
    assert row.expires_at > time.time() + 6 * 24 * 3600


def test_logout_revokes(client: TestClient):
    token = auth_tokens.issue_token()
    login_sessions.revoke(token)
    assert auth_tokens.verify_token(token) is False


def test_staff_token_persists_and_pin_reset_logs_out(client: TestClient):
    sid, token = _signup_and_approve(client, "로그인유지")
    assert auth_tokens.verify_token(token) is False  # 직원 토큰은 관리자용이 아님
    assert client.get("/api/me", headers=_auth(token)).status_code == 200

    assert client.post(f"/api/staff-accounts/reset-pin/{sid}").status_code == 200
    assert client.get("/api/me", headers=_auth(token)).status_code == 401
