"""
스케줄 표 2개 (스펙 5 자동배치, 6.1 결과 수정, 7 QR 공유).

- Schedule      : 한 매장의 '한 달치' 스케줄 1개. 공유코드(share_code)가 QR 대상.
- ScheduleEntry : 스케줄 안의 칸 1개 = (직원, 날짜) -> 근무코드.
"""

from datetime import date, datetime

from sqlmodel import Field, SQLModel, UniqueConstraint

from app.models.base import utcnow


class Schedule(SQLModel, table=True):
    __tablename__ = "schedule"
    __table_args__ = (UniqueConstraint("store_id", "year", "month", name="uq_schedule_store_month"),)

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)

    year: int
    month: int
    status: str = "draft"                    # ScheduleStatus: draft / confirmed
    edited: bool = False                     # 자동배치 후 사장님이 수동 수정했는지
    share_code: str | None = Field(default=None, unique=True, index=True)  # QR URL 용 고유코드
    published_at: datetime | None = None     # 직원에게 공개(공유)한 시각. 재공유 때마다 최신 시각으로 갱신.
    # True 면 이 달은 자동배치 실행을 서버가 거절한다 (실수로 덮어쓰기 방지). 수동 수정·공유는 그대로 가능.
    auto_locked: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class ScheduleEntry(SQLModel, table=True):
    __tablename__ = "schedule_entry"
    __table_args__ = (
        UniqueConstraint("schedule_id", "staff_id", "work_date", name="uq_entry_cell"),
    )

    id: int | None = Field(default=None, primary_key=True)
    schedule_id: int = Field(foreign_key="schedule.id", index=True)
    staff_id: int = Field(foreign_key="staff.id", index=True)

    work_date: date
    work_code: str          # WorkCode.code 값. 예: "O", "D/O", "연차", "&&"
    is_warning: bool = False  # 자동배치가 못 채운 슬롯 등 경고 표시용 (스펙 5-6)
