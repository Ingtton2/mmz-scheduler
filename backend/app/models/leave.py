"""
연차 관련 표 2개 (스펙 2.1 연차정보, 3장 연차/휴무 관리).

- LeaveBalance : 직원별 연차 '잔액' 정보. 부여연차(누적)·사용연차(누적)만 저장하고
                 잔여연차는 저장하지 않고 그때그때 계산한다 (스펙: "자동 계산").
- LeaveRequest : (과거 기록) 직원이 날짜로 신청하던 연차. 더는 새로 받지 않고, 자동배치에도
                 영향을 주지 않는다 — 조회용으로만 남겨둔다.
- MonthlyLeavePlan : 자동배치 실행 때 사장님이 정한 "직원별 그 달 연차 사용 개수". 실행할 때
                 사용연차(LeaveBalance.used)에서 차감하고, 같은 달을 다시 돌리면 이전 값만큼
                 되돌린 뒤 새 값으로 다시 차감한다.
- LeaveGrantLog : "연차 관리 > 연차 사용 현황" 탭의 부여 이력. 부여연차(granted)를
                  올릴 때마다 한 줄씩 남긴다 (월차 자동부여/1주년 부여/기존 데이터 이관 등).
- LeaveUsageLog : (과거 기록) 예전 승인 방식의 사용 이력. 새 사용 이력은 MonthlyLeavePlan.
"""

from datetime import date, datetime

from sqlmodel import Field, SQLModel, UniqueConstraint

from app.models.base import today_kst, utcnow


class LeaveBalance(SQLModel, table=True):
    __tablename__ = "leave_balance"

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)
    staff_id: int = Field(foreign_key="staff.id", unique=True)

    base_off_days: int = 0  # 기본휴무 (연차와 별개, 월 최소 휴무일수)
    granted: float = 0      # 부여연차 (누적)
    used: float = 0         # 사용연차 (누적)

    # --- 아래는 저장하지 않고 계산해서 응답에 실어줌 (app/schemas/leave.py) ---
    #   잔여연차 = 부여연차 - 사용연차


class LeaveRequest(SQLModel, table=True):
    __tablename__ = "leave_request"

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)
    staff_id: int = Field(foreign_key="staff.id", index=True)

    start_date: date                       # 연차 시작일 (쉬는 날)
    end_date: date                         # 연차 종료일 (포함). 하루면 start == end
    applied_at: date = Field(default_factory=today_kst)  # 신청일
    status: str = "requested"              # LeaveRequestStatus: requested / confirmed
    note: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class LeaveGrantLog(SQLModel, table=True):
    """부여 이력 (날짜, 대상자, 부여일수)."""

    __tablename__ = "leave_grant_log"

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)
    staff_id: int = Field(foreign_key="staff.id", index=True)

    granted_at: date = Field(default_factory=today_kst)  # 부여일
    days: float                                           # 부여일수
    note: str | None = None                               # "월차 자동부여" / "1주년 연차부여" / "기존 데이터 이관" 등
    created_at: datetime = Field(default_factory=utcnow)


class LeaveUsageLog(SQLModel, table=True):
    """사용 이력 (직원명, 사용일, 사용일수, 신청일, 사용 후 잔여연차).
    LeaveRequest 1건당 최대 1줄 — 승인되면 생기고, 승인이 취소되면 지워진다."""

    __tablename__ = "leave_usage_log"

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)
    staff_id: int = Field(foreign_key="staff.id", index=True)
    leave_request_id: int = Field(foreign_key="leave_request.id", unique=True)

    start_date: date        # 사용일 시작
    end_date: date          # 사용일 종료 (포함)
    days: float             # 사용일수
    applied_at: date        # 신청일 (LeaveRequest.applied_at 그대로)
    remaining_after: float  # 이 사용을 반영한 뒤의 잔여연차
    created_at: datetime = Field(default_factory=utcnow)


class MonthlyLeavePlan(SQLModel, table=True):
    """직원별 그 달 연차 사용 개수 (자동배치 실행 시 저장 + 사용연차 차감)."""

    __tablename__ = "monthly_leave_plan"
    __table_args__ = (
        UniqueConstraint("store_id", "year", "month", "staff_id", name="uq_leave_plan_cell"),
    )

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)
    staff_id: int = Field(foreign_key="staff.id", index=True)

    year: int
    month: int
    days: int               # 실제로 배치된 연차 개수 (요청보다 적을 수 있음)
    remaining_after: float  # 이 차감을 반영한 뒤의 잔여연차 (스냅샷)
    applied_at: date = Field(default_factory=today_kst)  # 마지막 자동배치 실행일
    created_at: datetime = Field(default_factory=utcnow)
