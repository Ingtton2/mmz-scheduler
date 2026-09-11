"""
관리자 로그인 (스펙 9 "사장님 정식 로그인 계정" 이전의 간단 버전).

  GET  /api/auth/status   로그인 기능이 켜져 있는지 (ADMIN_USER/ADMIN_PASS 설정 여부)
  POST /api/auth/login    아이디/비밀번호 확인 → 로그인 토큰 발급
  GET  /api/auth/me       가지고 있는 토큰이 아직 유효한지 확인
  POST /api/auth/logout   로그아웃 (토큰 폐기)

이 라우터는 main.py 의 관리자 인증 미들웨어에서 예외(공개) 경로로 취급된다 —
로그인 자체를 하려면 로그인 없이 이 주소들엔 접근할 수 있어야 하기 때문.
"""

import secrets

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.auth_tokens import issue_token, revoke_token, verify_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class LoginResponse(BaseModel):
    token: str


def _bearer_token(authorization: str) -> str:
    if authorization.startswith("Bearer "):
        return authorization[len("Bearer ") :]
    return ""


@router.get("/status")
def auth_status() -> dict:
    return {"enabled": settings.admin_auth_enabled}


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    if not settings.admin_auth_enabled:
        # ADMIN_USER/ADMIN_PASS 를 설정 안 한 경우(로컬 개발 등) — 로그인 기능 자체가 꺼짐.
        return LoginResponse(token=issue_token())

    ok = secrets.compare_digest(body.username, settings.admin_user) and secrets.compare_digest(
        body.password, settings.admin_pass
    )
    if not ok:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    return LoginResponse(token=issue_token())


@router.get("/me")
def me(authorization: str = Header(default="")) -> dict:
    if not settings.admin_auth_enabled:
        return {"ok": True}
    if not verify_token(_bearer_token(authorization)):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return {"ok": True}


@router.post("/logout")
def logout(authorization: str = Header(default="")) -> dict:
    revoke_token(_bearer_token(authorization))
    return {"ok": True}
