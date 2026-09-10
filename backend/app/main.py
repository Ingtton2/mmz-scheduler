"""
백엔드 서버의 시작점.

실행:  uvicorn app.main:app --reload
확인:  http://localhost:8000/health   (서버 살아있는지)
       http://localhost:8000/docs     (API 자동 문서 / 테스트 화면)
"""

import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import settings
from app.database import init_db

# 관리자 기본 인증에서 제외할 경로 (직원 QR 조회 / 헬스체크는 그대로 열림).
_OPEN_PREFIXES = ("/health", "/api/public")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버가 켜질 때 1회: 표 생성 + 기본 매장 준비.
    init_db()
    yield


app = FastAPI(title="mmz-scheduler API", version="0.1.0", lifespan=lifespan)

# 브라우저(프론트엔드)에서 이 서버로 요청을 보낼 수 있게 허용.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def admin_basic_auth(request: Request, call_next):
    """ADMIN_USER / ADMIN_PASS 환경변수가 있으면 관리자 API 에 HTTP 기본 인증을 건다."""
    if settings.admin_auth_enabled and request.method != "OPTIONS":
        path = request.url.path
        if not any(path.startswith(p) for p in _OPEN_PREFIXES):
            ok = False
            auth = request.headers.get("authorization", "")
            if auth.startswith("Basic "):
                import base64

                try:
                    user, _, pw = base64.b64decode(auth[6:]).decode().partition(":")
                    ok = secrets.compare_digest(user, settings.admin_user) and (
                        secrets.compare_digest(pw, settings.admin_pass)
                    )
                except Exception:
                    ok = False
            if not ok:
                return Response(
                    status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="mmz-scheduler"'},
                )
    return await call_next(request)


@app.get("/health")
def health() -> dict:
    """서버가 살아있는지 확인용."""
    return {"status": "ok", "app": "mmz-scheduler"}


# 실제 기능 주소들 (/api/...)
app.include_router(api_router, prefix="/api")
