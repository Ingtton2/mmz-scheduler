"""연차 부여/사용 현황 API 데이터 형태 ("연차 관리 > 연차 사용 현황" 탭)."""

from datetime import date

from pydantic import BaseModel, Field


class GrantCandidate(BaseModel):
    """이번 달 부여 대상 (자동 계산, 저장 안 함)."""

    staff_id: int
    staff_name: str
    hire_date: date
    kind: str  # "monthly"(월차 1개) | "anniversary"(1주년, 15일)
    days: float


class LeaveGrantCreate(BaseModel):
    staff_id: int
    days: float = Field(gt=0)
    note: str | None = None
    granted_at: date | None = None  # 비우면 오늘 날짜


class LeaveGrantRead(BaseModel):
    id: int
    staff_id: int
    staff_name: str
    granted_at: date
    days: float
    note: str | None

    model_config = {"from_attributes": True}


class LeaveUsageLogRead(BaseModel):
    id: int
    staff_id: int
    staff_name: str
    start_date: date
    end_date: date
    days: float
    applied_at: date
    remaining_after: float

    model_config = {"from_attributes": True}
