"""
공휴일(대체공휴일 포함) 등록 API 데이터 형태.

관리자가 날짜 + 이름(예: "추석")을 직접 등록한다. 자동배치엔 영향 없음 — 스케줄표 표시 전용.
"""

from datetime import date

from pydantic import BaseModel, Field


class HolidayCreate(BaseModel):
    date: date
    name: str = Field(min_length=1, max_length=50)


class HolidayItem(BaseModel):
    id: int
    date: date
    name: str
