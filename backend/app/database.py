"""
데이터베이스 연결 설정.

로컬 개발은 SQLite(파일 1개), 실제 배포는 PostgreSQL.
`DATABASE_URL` 환경변수만 바꾸면 코드 수정 없이 전환됩니다.
"""

from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

# SQLite 는 여러 스레드에서 접근할 때 옵션이 하나 필요합니다.
connect_args = {"check_same_thread": False} if _is_sqlite else {}

# PostgreSQL: 유휴 연결이 끊겨도 자동 복구되도록 pre_ping / recycle 설정.
engine_kwargs: dict = {"echo": False, "connect_args": connect_args}
if not _is_sqlite:
    engine_kwargs.update(pool_pre_ping=True, pool_recycle=300)

engine = create_engine(settings.database_url, **engine_kwargs)


def _ensure_store_columns() -> None:
    """`create_all` 은 이미 있는 표에 새 컬럼을 추가해주지 않는다 (마이그레이션 도구 없음).
    배포된 DB에 이미 store 표가 있으면 새로 추가된 컬럼만 여기서 수동으로 붙여준다."""
    with engine.begin() as conn:
        if _is_sqlite:
            cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(store)").fetchall()}
        else:
            cols = {
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'store'"
                    )
                ).fetchall()
            }
        if "daily_headcount_target" not in cols:
            conn.execute(
                text("ALTER TABLE store ADD COLUMN daily_headcount_target INTEGER DEFAULT 0")
            )


def init_db() -> None:
    """앱이 처음 켜질 때: 표를 만들고, 기본 매장 1개를 보장합니다."""
    import app.models  # noqa: F401  (모든 표를 SQLModel 에 등록시키기 위해)
    from app.models import DEFAULT_STORE_ID, Store

    SQLModel.metadata.create_all(engine)
    _ensure_store_columns()

    with Session(engine) as session:
        existing = session.exec(select(Store).where(Store.id == DEFAULT_STORE_ID)).first()
        if existing is None:
            session.add(Store(id=DEFAULT_STORE_ID, name="우리 식당"))
            session.commit()


def get_session() -> Generator[Session, None, None]:
    """API 함수가 DB 를 쓸 때 이걸 통해 세션을 하나 빌려갑니다."""
    with Session(engine) as session:
        yield session
