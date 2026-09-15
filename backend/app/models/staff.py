"""
Staff = 직원 (스펙 2.1, 2.2).

enum 값들은 문자열로 저장됩니다 (예: position = "both").
검증은 API 스키마(app/schemas/staff.py)에서 합니다.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class Staff(SQLModel, table=True):
    __tablename__ = "staff"

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)

    name: str
    # 고용형태는 일반 직원만 해당. 사장님이면 None.
    employment_type: str | None = None  # EmploymentType: full_time / part_time
    position: str                       # Position: hall / kitchen / both
    role: str = "staff"                 # StaffRole: staff / owner

    # 근무 가능 요일: "0,1,2,3,4,5,6" (0=월 ~ 6=일). 기본은 전체.
    # 파트타임처럼 특정 요일만 나오는 경우 여기서 제한한다.
    work_weekdays: str = "0,1,2,3,4,5,6"
    # True 면 위 요일에는 (연차만 아니면) 항상 배치한다. 파트타임 고정 근무용.
    fixed_schedule: bool = False

    is_active: bool = True         # 퇴사 시 False (기록은 남김)
    sort_order: int = 0            # 스케줄 표에서 보여줄 순서 (작을수록 위). 사장님은 항상 맨 아래.
    created_at: datetime = Field(default_factory=utcnow)
