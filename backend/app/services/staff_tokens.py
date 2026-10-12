"""
직원(셀프서비스) 로그인 토큰. 관리자 토큰(auth_tokens.py)과 같은 DB 표를 쓰지만 kind 가 달라서
완전히 별도 네임스페이스 — 직원 토큰으로 관리자 API 를 쓸 수 없고, 그 반대도 마찬가지.
서버가 재시작돼도 로그인이 유지되고, 14일 안에 한 번이라도 쓰면 계속 연장된다.
"""

from app.services import login_sessions

_KIND = "staff"
_TTL_SECONDS = 14 * 24 * 3600  # 직원 로그인 유지 기간: 마지막 사용 후 최대 14일


def issue_token(staff_id: int) -> str:
    return login_sessions.issue(_KIND, _TTL_SECONDS, staff_id=staff_id)


def verify_token(token: str) -> int | None:
    """유효하면 staff_id, 아니면 None."""
    row = login_sessions.verify(_KIND, token, _TTL_SECONDS)
    return row.staff_id if row is not None else None


def revoke_token(token: str) -> None:
    login_sessions.revoke(token)


def revoke_staff(staff_id: int) -> None:
    login_sessions.revoke_staff(staff_id)
