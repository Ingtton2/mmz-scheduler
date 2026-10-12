"""
LoginSession = 로그인 유지 정보 (관리자/직원 공용). 로그인 1번 = 행 1개.

예전엔 서버 메모리에만 들고 있어서, Render 무료 서버가 잠들었다 깨어나거나 새로 배포될 때마다
모두 로그아웃됐다. DB 에 저장하면 서버가 재시작돼도 로그인이 유지된다.

- token_hash : 토큰 원문이 아니라 SHA-256 해시만 저장 (DB 가 유출돼도 토큰으로 로그인 불가)
- kind       : "admin"(사장님 관리자 화면) / "staff"(직원 셀프서비스) — 서로 섞이지 않음
- staff_id   : kind="staff" 일 때 누구인지
- expires_at : 만료 시각 (epoch 초). 자주 쓰면 자동 연장된다 (services/login_sessions.py)
"""

from sqlmodel import Field, SQLModel


class LoginSession(SQLModel, table=True):
    __tablename__ = "login_session"

    token_hash: str = Field(primary_key=True)
    kind: str = Field(index=True)  # admin | staff
    staff_id: int | None = Field(default=None, foreign_key="staff.id", index=True)
    expires_at: float = Field(index=True)
    created_at: float
