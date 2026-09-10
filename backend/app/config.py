"""
앱 설정값을 한곳에서 관리합니다.
.env 파일(또는 환경변수)에서 값을 읽고, 없으면 여기 적힌 기본값을 씁니다.

로컬 개발  : 아무 설정 없이 SQLite(app.db) 로 동작
실제 배포  : DATABASE_URL(PostgreSQL), PUBLIC_BASE_URL, FRONTEND_ORIGINS 를 환경변수로 지정
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 데이터베이스 접속 주소.
    #   로컬: sqlite:///./app.db  (기본값)
    #   배포: Render 등이 주는 postgresql://... 주소를 환경변수 DATABASE_URL 로 넣음
    database_url: str = "sqlite:///./app.db"

    # 브라우저 보안(CORS) 허용 주소. 쉼표로 여러 개 가능.
    #   예: "http://localhost:5173,https://mmz-scheduler.vercel.app"
    frontend_origins: str = "http://localhost:5173"

    # QR 코드에 들어갈 공개 URL의 앞부분 (직원이 접속할 프론트엔드 주소).
    public_base_url: str = "http://localhost:5173"

    # (선택) 관리자 API 보호용 아이디/비밀번호. 둘 다 있으면 /api 에 기본 인증이 걸림
    # ('/api/public/*', '/health' 는 예외 — 직원 QR 조회는 그대로 열림).
    admin_user: str = ""
    admin_pass: str = ""

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # Render/Heroku 는 옛 형식 'postgres://' 를 주기도 하고,
        # SQLAlchemy 는 'postgresql://' 를 psycopg2 로 해석한다.
        # 우리는 psycopg(v3) 를 쓰므로 '+psycopg' 를 붙여준다.
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://") :]
        return v

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]

    @property
    def admin_auth_enabled(self) -> bool:
        return bool(self.admin_user and self.admin_pass)


# 앱 전체에서 이 하나를 가져다 씁니다:  from app.config import settings
settings = Settings()
