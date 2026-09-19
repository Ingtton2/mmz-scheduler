"""사전 휴무 신청 API 데이터 형태 (스펙 3.1) — 기간(시작일~종료일) 단위."""

from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import LeaveRequestStatus
from app.schemas.leave import _DateRange


class DayOffRequestCreate(_DateRange):
    staff_id: int
    note: str | None = None
    status: LeaveRequestStatus = LeaveRequestStatus.REQUESTED
    applied_at: date | None = None  # 비우면 오늘 날짜로 저장
    reject_reason: str | None = None  # status 가 rejected 일 때 필수


class DayOffRequestUpdate(BaseModel):
    status: LeaveRequestStatus | None = None
    reject_reason: str | None = None  # status 를 rejected 로 바꿀 때 필수
    note: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    applied_at: date | None = None


class DayOffRequestRead(BaseModel):
    id: int
    staff_id: int
    staff_name: str
    start_date: date
    end_date: date
    days: int
    applied_at: date
    status: str
    note: str | None
    reject_reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
