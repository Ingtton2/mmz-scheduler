"""
관리자(사장님) 로그인 토큰. 실제 저장은 DB(login_session 표) — services/login_sessions.py 참고.
서버가 재시작돼도 로그인이 유지되고, 7일 안에 한 번이라도 쓰면 계속 연장된다.
"""

from app.services import login_sessions

_KIND = "admin"
_TTL_SECONDS = 7 * 24 * 3600  # 로그인 유지 기간: 마지막 사용 후 최대 7일


def issue_token() -> str:
    return login_sessions.issue(_KIND, _TTL_SECONDS)


def verify_token(token: str) -> bool:
    return login_sessions.verify(_KIND, token, _TTL_SECONDS) is not None


def revoke_token(token: str) -> None:
    login_sessions.revoke(token)
