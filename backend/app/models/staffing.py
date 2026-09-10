"""
StaffingRequirement = 요일/시간대별 필요 인원 고정값 (스펙 4).

예: "매주 화요일 디너에 홀 최소 3명, 주방 최소 3명".
자동배치 엔진이 이 값을 제약조건으로 사용.
"""

from sqlmodel import Field, SQLModel


class StaffingRequirement(SQLModel, table=True):
    __tablename__ = "staffing_requirement"

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)

    weekday: int              # 0=월 ~ 6=일
    time_slot: str = "close"  # TimeSlot: open / mid / close
    position: str             # "hall" / "kitchen"
    min_headcount: int        # 최소 인원
