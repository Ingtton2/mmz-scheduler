"""
DayOffRequest = 사전 휴무 신청 (스펙 3.1).

연차와 별개 개념:
  - 연차(LeaveRequest): 그날 쉬고 총 근무일수도 줄어듦, 잔여연차 차감
  - 사전 휴무 신청: 그날 배치 제외되지만 총 근무일수는 유지 (자동배치가 다른 날로 옮겨 채움),
                   연차 차감 없음. 직원 1명당 한 달 최대 20일.

자동배치에서는 연차처럼 하드 제약(그 날짜 배치 금지)으로 쓰지만,
근무일수/연차 계산에서는 연차와 분리해서 처리한다.
"""

from datetime import date, datetime

from sqlmodel import Field, SQLModel

from app.models.base import utcnow

MAX_PER_MONTH = 20


class DayOffRequest(SQLModel, table=True):
    __tablename__ = "day_off_request"

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)
    staff_id: int = Field(foreign_key="staff.id", index=True)

    start_date: date                     # 근무 불가 시작일
    end_date: date                       # 근무 불가 종료일 (포함). 하루면 start == end
    applied_at: date = Field(default_factory=date.today)  # 신청일
    status: str = "requested"            # LeaveRequestStatus 재사용: requested / confirmed / rejected
    note: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
