"""
연차 관련 표 2개 (스펙 2.1 연차정보, 3장 연차/휴무 관리).

- LeaveBalance : 직원별 연차 '잔액' 정보. 합연차·잔여연차는 저장하지 않고
                 입력값으로 그때그때 계산 (스펙: "자동 계산").
- LeaveRequest : 직원이 미리 신청하는 연차 기간(시작일~종료일). 자동배치 시 최우선 고정.
"""

from datetime import date, datetime

from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class LeaveBalance(SQLModel, table=True):
    __tablename__ = "leave_balance"

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)
    staff_id: int = Field(foreign_key="staff.id", unique=True)

    base_off_days: int = 0     # 기본휴무
    prev_remaining: float = 0  # 전월잔여연차
    prev_accrued: float = 0    # 전월발생연차
    used: float = 0            # 연차사용

    # --- 아래 둘은 저장하지 않고 계산해서 응답에 실어줌 (app/schemas/leave.py) ---
    #   합연차   = prev_remaining + prev_accrued
    #   잔여연차 = 합연차 - used


class LeaveRequest(SQLModel, table=True):
    __tablename__ = "leave_request"

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)
    staff_id: int = Field(foreign_key="staff.id", index=True)

    start_date: date                       # 연차 시작일
    end_date: date                         # 연차 종료일 (포함). 하루면 start == end
    status: str = "requested"              # LeaveRequestStatus: requested / confirmed
    note: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
