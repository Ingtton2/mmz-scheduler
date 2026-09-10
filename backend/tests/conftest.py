"""
테스트 공통 준비.

테스트는 진짜 app.db 를 건드리지 않도록, 임시 폴더에 별도 SQLite 파일을 씁니다.
(이 파일은 app.* 를 import 하기 전에 먼저 실행되어 환경변수를 세팅합니다.)
"""

import os
import tempfile

import pytest

_tmp_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db}"

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

from app.database import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import DEFAULT_STORE_ID, Store  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    init_db()
    yield


@pytest.fixture(autouse=True)
def _clean_db():
    """테스트마다 표를 비우고 기본 매장만 남긴다 (테스트 격리)."""
    with Session(engine) as s:
        for table in reversed(SQLModel.metadata.sorted_tables):
            s.execute(table.delete())
        s.commit()
        s.add(Store(id=DEFAULT_STORE_ID, name="우리 식당"))
        s.commit()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
