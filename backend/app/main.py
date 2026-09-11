"""
백엔드 서버의 시작점.

실행:  uvicorn app.main:app --reload
확인:  http://localhost:8000/health   (서버 살아있는지)
       http://localhost:8000/docs     (API 자동 문서 / 테스트 화면)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import settings
from app.database import engine, init_db
from app.services.auth_tokens import verify_token

# 관리자 로그인에서 제외할 경로
# (직원 QR 조회 / 헬스체크 / 로그인 자체는 로그인 없이 열려 있어야 함).
_OPEN_PREFIXES = ("/health", "/api/public", "/api/auth")


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
async def admin_auth(request: Request, call_next):
    """ADMIN_USER / ADMIN_PASS 환경변수가 있으면, 로그인 토큰(Authorization: Bearer ...)이
    있어야 관리자 API 를 쓸 수 있다. 토큰은 POST /api/auth/login 으로 받는다."""
    if settings.admin_auth_enabled and request.method != "OPTIONS":
        path = request.url.path
        if not any(path.startswith(p) for p in _OPEN_PREFIXES):
            auth = request.headers.get("authorization", "")
            token = auth[len("Bearer ") :] if auth.startswith("Bearer ") else ""
            if not verify_token(token):
                return Response(
                    status_code=401,
                    content='{"detail":"로그인이 필요합니다."}',
                    media_type="application/json",
                )
    return await call_next(request)


@app.get("/health")
def health() -> dict:
    """서버가 살아있는지 + 어떤 DB 에 붙어 있는지 확인용 (비밀번호 등은 노출 안 함)."""
    return {
        "status": "ok",
        "app": "mmz-scheduler",
        "db": engine.dialect.name,  # "postgresql" 이어야 정상 (배포 환경). 로컬은 "sqlite".
        "public_base_url": settings.public_base_url,
        "frontend_origins": settings.cors_origins,
    }


# 실제 기능 주소들 (/api/...)
app.include_router(api_router, prefix="/api")
