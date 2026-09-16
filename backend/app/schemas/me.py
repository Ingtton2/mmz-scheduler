"""직원 셀프서비스 "내 연차/사전휴무/스케줄" API 데이터 형태 (스펙 9-4, 9-5).

staff_id 는 요청 바디가 아니라 로그인 토큰에서 나온다 — 다른 직원 이름으로
신청하는 걸 막기 위해 클라이언트가 staff_id 를 지정할 수 없게 한다.
"""

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.leave import _DateRange
from app.schemas.schedule import ShiftSummary


class MyRequestCreate(_DateRange):
    note: str | None = None


class MyLeaveRequestOut(BaseModel):
    id: int
    start_date: date
    end_date: date
    days: int
    applied_at: date
    status: str
    note: str | None
    created_at: datetime


class MyDayOffRequestOut(BaseModel):
    id: int
    start_date: date
    end_date: date
    days: int
    note: str | None
    created_at: datetime


class MyScheduleResult(BaseModel):
    year: int
    month: int
    days: list[str]
    cells: dict[str, str]
    summary: ShiftSummary
    generated_at: datetime | None = None
