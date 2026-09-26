"""휴가 일정 공유 메모판 요청/응답 모양."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class DateRange(BaseModel):
    start: date
    end: date


class VacationNoteSave(BaseModel):
    """본인 메모 통째로 저장 (자동 저장이 매번 전체를 보낸다)."""

    months: list[str] = Field(default_factory=list, max_length=60)
    ranges: list[DateRange] = Field(default_factory=list, max_length=200)
    no_plans: bool = False
    memo: str = Field(default="", max_length=200)  # 저장할 때 60자로 자른다


class VacationNoteOut(BaseModel):
    staff_id: int
    name: str
    months: list[str]
    ranges: list[DateRange]
    no_plans: bool
    memo: str
    updated_at: datetime


class VacationBoard(BaseModel):
    """메모판 전체 현황. months = 화면에 보여줄 달 범위 (이번 달 ~ WINDOW_END)."""

    months: list[str]
    today: date
    notes: list[VacationNoteOut]
    # 직원 화면에서만: 나의 staff_id, 내가 적을 수 있는지 (정직원·점장만)
    my_staff_id: int | None = None
    my_name: str | None = None
    can_edit: bool = False
