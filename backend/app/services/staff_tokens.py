"""
직원(셀프서비스) 로그인 토큰 저장소. 관리자 토큰(auth_tokens.py)과 같은 패턴이지만
완전히 별도 네임스페이스 — 토큰 하나가 "어느 직원(staff_id)인지"를 들고 있다.

메모리에만 저장 (서버 재시작 시 초기화 — Render 무료 플랜 특성상 admin 토큰과 동일한
트레이드오프, 재로그인하면 됨).
"""

import secrets
import time

_TTL_SECONDS = 14 * 24 * 3600  # 직원 로그인 유지 기간: 14일

_tokens: dict[str, tuple[int, float]] = {}  # token -> (staff_id, 만료시각)


def issue_token(staff_id: int) -> str:
    token = secrets.token_urlsafe(32)
    _tokens[token] = (staff_id, time.time() + _TTL_SECONDS)
    return token


def verify_token(token: str) -> int | None:
    """유효하면 staff_id, 아니면 None."""
    if not token:
        return None
    row = _tokens.get(token)
    if row is None:
        return None
    staff_id, expires_at = row
    if expires_at < time.time():
        _tokens.pop(token, None)
        return None
    return staff_id


def revoke_token(token: str) -> None:
    _tokens.pop(token, None)
