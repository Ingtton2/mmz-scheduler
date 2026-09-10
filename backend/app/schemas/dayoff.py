"""사전 휴무 신청 API 데이터 형태 (스펙 3.1) — 기간(시작일~종료일) 단위."""

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.leave import _DateRange


class DayOffRequestCreate(_DateRange):
    staff_id: int
    note: str | None = None


class DayOffRequestRead(BaseModel):
    id: int
    staff_id: int
    staff_name: str
    start_date: date
    end_date: date
    days: int
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
