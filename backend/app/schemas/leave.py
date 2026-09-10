"""
연차 관련 API 데이터 형태 (스펙 3).

- LeaveBalanceInput : 화면 -> 서버 (직원의 연차 숫자 입력값)
- LeaveBalanceRead  : 서버 -> 화면 (입력값 + 합연차/잔여연차 자동계산 포함)
- LeaveRequestCreate/Read/Update : 연차 신청 (지금은 사장님이 대신 입력)
"""

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import LeaveRequestStatus
from app.services import leave_calc

MAX_RANGE_DAYS = 366  # 한 번에 신청 가능한 최대 기간(일)


class _DateRange(BaseModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def _check(self):
        if self.end_date < self.start_date:
            raise ValueError("종료일이 시작일보다 빠릅니다.")
        if (self.end_date - self.start_date).days + 1 > MAX_RANGE_DAYS:
            raise ValueError("한 번에 신청할 수 있는 기간이 너무 깁니다.")
        return self


class LeaveBalanceInput(BaseModel):
    base_off_days: int = Field(default=0, ge=0)     # 기본휴무
    prev_remaining: float = Field(default=0, ge=0)  # 전월잔여연차
    prev_accrued: float = Field(default=0, ge=0)    # 전월발생연차
    used: float = Field(default=0, ge=0)            # 연차사용


class LeaveBalanceRead(BaseModel):
    base_off_days: int
    prev_remaining: float
    prev_accrued: float
    used: float
    total_accrued: float  # 합연차 (자동계산)
    remaining: float       # 잔여연차 (자동계산)

    @classmethod
    def from_values(
        cls, base_off_days: int, prev_remaining: float, prev_accrued: float, used: float
    ) -> "LeaveBalanceRead":
        return cls(
            base_off_days=base_off_days,
            prev_remaining=prev_remaining,
            prev_accrued=prev_accrued,
            used=used,
            total_accrued=leave_calc.total_accrued(prev_remaining, prev_accrued),
            remaining=leave_calc.remaining(prev_remaining, prev_accrued, used),
        )


class LeaveRequestCreate(_DateRange):
    staff_id: int
    note: str | None = None
    status: LeaveRequestStatus = LeaveRequestStatus.REQUESTED


class LeaveRequestUpdate(BaseModel):
    status: LeaveRequestStatus | None = None
    note: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class LeaveRequestRead(BaseModel):
    id: int
    staff_id: int
    staff_name: str
    start_date: date
    end_date: date
    days: int              # 기간 일수 (양끝 포함)
    status: str
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
