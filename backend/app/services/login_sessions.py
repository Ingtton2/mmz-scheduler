"""
관리자/직원 로그인 토큰을 DB(login_session 표)에 저장·확인하는 공용 로직.
auth_tokens.py(관리자), staff_tokens.py(직원)가 이걸 kind 만 바꿔서 쓴다.

자동 연장(슬라이딩 만료): 남은 기간이 절반 아래로 떨어진 상태에서 앱을 쓰면 만료를 다시
처음 길이로 늘린다. 그래서 꾸준히 쓰는 사람은 로그인이 풀리지 않고, 오래(유지 기간 이상)
안 쓴 기기만 다시 로그인하게 된다. 매 요청마다 DB 에 쓰지 않도록 절반 기준을 둔다.
"""

import hashlib
import secrets
import time

from sqlalchemy import delete
from sqlmodel import Session

from app.database import engine
from app.models import LoginSession


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue(kind: str, ttl_seconds: int, staff_id: int | None = None) -> str:
    token = secrets.token_urlsafe(32)
    now = time.time()
    with Session(engine) as session:
        # 김에 만료된 로그인 정리 (표가 끝없이 커지지 않게).
        session.exec(delete(LoginSession).where(LoginSession.expires_at < now))
        session.add(
            LoginSession(
                token_hash=_hash(token),
                kind=kind,
                staff_id=staff_id,
                expires_at=now + ttl_seconds,
                created_at=now,
            )
        )
        session.commit()
    return token


def verify(kind: str, token: str, ttl_seconds: int) -> LoginSession | None:
    """유효하면 LoginSession, 아니면 None. 필요하면 만료를 연장한다."""
    if not token:
        return None
    now = time.time()
    with Session(engine) as session:
        row = session.get(LoginSession, _hash(token))
        if row is None or row.kind != kind:
            return None
        if row.expires_at < now:
            session.delete(row)
            session.commit()
            return None
        if row.expires_at - now < ttl_seconds / 2:
            row.expires_at = now + ttl_seconds
            session.add(row)
            session.commit()
            session.refresh(row)
        session.expunge(row)
        return row


def revoke(token: str) -> None:
    with Session(engine) as session:
        row = session.get(LoginSession, _hash(token))
        if row is not None:
            session.delete(row)
            session.commit()


def revoke_staff(staff_id: int) -> None:
    """그 직원의 모든 기기 로그인 해제 (PIN 초기화·직원 삭제 때)."""
    with Session(engine) as session:
        session.exec(
            delete(LoginSession).where(
                LoginSession.kind == "staff", LoginSession.staff_id == staff_id
            )
        )
        session.commit()
