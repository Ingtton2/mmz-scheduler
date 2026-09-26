"""
PersonalScheduleNote = "휴가 일정 공유" 메모판. 직원 1명당 1줄.

직원들이 "몇 월(며칠)에 개인 일정이 있다"를 미리 적어두고 서로 겹치지 않게
조율하는 순수 참고용 게시판이다. 연차 신청·사전휴무 신청·자동배치와는 무관하다
(승인 없음, 잔여연차 계산에도 영향 없음).

- months : 일정 있다고 표시한 "YYYY-MM" 목록
- ranges : 그 달 안에서 알고 있는 날짜 구간 [{"start": "YYYY-MM-DD", "end": ...}] (선택)
- no_plans : "특별한 일정 없어요" 표시 (months 가 있으면 항상 False)
- memo : 자유 메모 60자, 전체 공개

본인 것을 저장하면 통째로 덮어쓰고(upsert), 내용이 모두 비면 행을 지운다.
"""

from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.base import utcnow

MEMO_MAX = 60


class PersonalScheduleNote(SQLModel, table=True):
    __tablename__ = "personal_schedule_note"

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)
    staff_id: int = Field(foreign_key="staff.id", unique=True, index=True)

    months: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    ranges: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    no_plans: bool = False
    memo: str = ""

    updated_at: datetime = Field(default_factory=utcnow)
