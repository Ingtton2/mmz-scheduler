"""연차 사용 이력 만들기 — 관리자 "연차 사용 현황" 탭과 직원 "내 연차"가 함께 쓴다.

두 종류를 합쳐 최신순으로 돌려준다:
  - 예전 승인 방식 기록 (LeaveUsageLog)
  - 자동배치 방식 기록 (MonthlyLeavePlan + 그 달 근무표에 실제로 잡힌 "연차" 날짜)
staff_id 를 주면 그 직원 것만.
"""

from datetime import date

from sqlmodel import Session, select

from app.models import (
    DEFAULT_STORE_ID,
    LeaveUsageLog,
    MonthlyLeavePlan,
    Schedule,
    ScheduleEntry,
    Staff,
)
from app.schemas.leave_usage import LeaveUsageLogRead


def build_usage_log(session: Session, staff_id: int | None = None) -> list[LeaveUsageLogRead]:
    out: list[tuple[object, LeaveUsageLogRead]] = []

    legacy_q = (
        select(LeaveUsageLog, Staff)
        .join(Staff, Staff.id == LeaveUsageLog.staff_id)
        .where(LeaveUsageLog.store_id == DEFAULT_STORE_ID)
    )
    if staff_id is not None:
        legacy_q = legacy_q.where(LeaveUsageLog.staff_id == staff_id)
    legacy = session.exec(legacy_q).all()
    for u, s in legacy:
        out.append(
            (
                u.created_at,
                LeaveUsageLogRead(
                    id=u.id,
                    staff_id=u.staff_id,
                    staff_name=s.name,
                    start_date=u.start_date,
                    end_date=u.end_date,
                    days=u.days,
                    applied_at=u.applied_at,
                    remaining_after=u.remaining_after,
                ),
            )
        )

    plans_q = (
        select(MonthlyLeavePlan, Staff)
        .join(Staff, Staff.id == MonthlyLeavePlan.staff_id)
        .where(MonthlyLeavePlan.store_id == DEFAULT_STORE_ID, MonthlyLeavePlan.days > 0)
    )
    if staff_id is not None:
        plans_q = plans_q.where(MonthlyLeavePlan.staff_id == staff_id)
    plans = session.exec(plans_q).all()
    for p, s in plans:
        dates = sorted(
            e.work_date
            for e in session.exec(
                select(ScheduleEntry)
                .join(Schedule, Schedule.id == ScheduleEntry.schedule_id)
                .where(
                    Schedule.store_id == DEFAULT_STORE_ID,
                    Schedule.year == p.year,
                    Schedule.month == p.month,
                    ScheduleEntry.staff_id == p.staff_id,
                    ScheduleEntry.work_code == "연차",
                )
            ).all()
        )
        first = date(p.year, p.month, 1)
        out.append(
            (
                p.created_at,
                LeaveUsageLogRead(
                    id=-p.id,  # 예전 이력 id 와 안 겹치게 음수
                    staff_id=p.staff_id,
                    staff_name=s.name,
                    start_date=dates[0] if dates else first,
                    end_date=dates[-1] if dates else first,
                    days=p.days,
                    applied_at=p.applied_at,
                    remaining_after=p.remaining_after,
                    year_month=f"{p.year}-{p.month:02d}",
                    dates=dates,
                ),
            )
        )

    out.sort(key=lambda t: t[0], reverse=True)
    return [row for _, row in out]
