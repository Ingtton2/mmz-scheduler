"""
Store = 매장. 모든 데이터의 최상위 소속 (스펙 10.1).

지금은 매장이 1개뿐이지만, 처음부터 '매장 1개 = 레코드 1줄' 구조로 시작해
나중에 여러 매장 서비스로 확장할 때 구조를 갈아엎지 않아도 되게 함.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import utcnow

# 지금은 매장이 하나뿐 → 이 id 를 기본값으로 씀. 멀티매장 되면 제거.
DEFAULT_STORE_ID = 1


class Store(SQLModel, table=True):
    __tablename__ = "store"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=utcnow)
