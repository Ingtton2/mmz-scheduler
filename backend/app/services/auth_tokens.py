"""
아주 단순한 로그인 토큰 저장소 (스펙 9 "사장님 정식 로그인 계정" 이전의 임시 버전).

- DB 없이 메모리에만 토큰을 들고 있음 (사장님 1명, 서버 인스턴스 1개 전제).
- 서버가 재시작되면(예: Render 무료 플랜이 잠들었다 깨어날 때) 토큰이 초기화되어
  다시 로그인해야 함 — 지금 단계에서는 이 정도로 충분.
- 나중에 직원 계정(스펙 9)까지 생기면 이 파일을 DB 기반 세션/JWT 로 교체하면 됨.
"""

import secrets
import time

_TTL_SECONDS = 7 * 24 * 3600  # 로그인 유지 기간: 7일

_tokens: dict[str, float] = {}  # token -> 만료 시각(epoch seconds)


def issue_token() -> str:
    token = secrets.token_urlsafe(32)
    _tokens[token] = time.time() + _TTL_SECONDS
    return token


def verify_token(token: str) -> bool:
    if not token:
        return False
    expires_at = _tokens.get(token)
    if expires_at is None:
        return False
    if expires_at < time.time():
        _tokens.pop(token, None)
        return False
    return True


def revoke_token(token: str) -> None:
    _tokens.pop(token, None)
