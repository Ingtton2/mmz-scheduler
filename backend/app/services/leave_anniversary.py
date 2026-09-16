"""
연차 자동부여 후보 계산 ("연차 관리 > 연차 사용 현황" 탭의 "이번 달 부여 대상" 카드).

규칙 (사용자 지정):
  - 입사 후 1년 미만: 매달 입사일과 같은 날짜(월급여일)가 될 때마다 "월차 1개" 부여 대상.
  - 입사 1주년: 그 달에 "연차 15일" 부여 대상.

이미 이번 달에 부여 기록(LeaveGrantLog)이 있는 직원은 후보에서 뺀다
(같은 달에 중복으로 버튼을 눌러 두 번 주는 걸 막기 위해).
"""

import calendar
from datetime import date

from sqlmodel import Session, select

from app.models import DEFAULT_STORE_ID, LeaveGrantLog, Staff
from app.schemas.staff import has_leave_balance

MONTHLY_GRANT_DAYS = 1.0
ANNIVERSARY_GRANT_DAYS = 15.0


def _add_months(d: date, months: int) -> date:
    """d 로부터 months 개월 후의 '같은 날'. 그 달에 그 날짜가 없으면 말일로 맞춘다."""
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def grant_kind_for_month(hire_date: date, year: int, month: int) -> tuple[str, float] | None:
    """이 달(year, month)에 hire_date 기준 월급여일이 걸리는지.
    ("monthly", 1) / ("anniversary", 15) / 해당 없으면 None."""
    for n in range(1, 13):
        anniv = _add_months(hire_date, n)
        if anniv.year == year and anniv.month == month:
            if n == 12:
                return ("anniversary", ANNIVERSARY_GRANT_DAYS)
            return ("monthly", MONTHLY_GRANT_DAYS)
    return None


def list_grant_candidates(session: Session, today: date) -> list[dict]:
    """이번 달(today 기준) 부여 대상 직원 목록."""
    year, month = today.year, today.month
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    staff_rows = session.exec(
        select(Staff).where(
            Staff.store_id == DEFAULT_STORE_ID,
            Staff.is_active == True,  # noqa: E712
        )
    ).all()

    out: list[dict] = []
    for s in staff_rows:
        if s.hire_date is None or not has_leave_balance(s.role, s.employment_type):
            continue
        kind_days = grant_kind_for_month(s.hire_date, year, month)
        if kind_days is None:
            continue
        already = session.exec(
            select(LeaveGrantLog).where(
                LeaveGrantLog.staff_id == s.id,
                LeaveGrantLog.granted_at >= month_start,
                LeaveGrantLog.granted_at <= month_end,
            )
        ).first()
        if already is not None:
            continue
        kind, days = kind_days
        out.append(
            {
                "staff_id": s.id,
                "staff_name": s.name,
                "hire_date": s.hire_date,
                "kind": kind,
                "days": days,
            }
        )
    return out
