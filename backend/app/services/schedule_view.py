"""저장된 스케줄을 "공개용" 모양(PublicScheduleResult)으로 조립.

QR 공유 화면(routes_public.py)과 직원 로그인 후 "이번 달 전체 스케줄"
(routes_me.py) 이 같은 모양의 데이터를 쓰므로 여기 한 곳에 모아둔다.
둘 다 호출 전에 스케줄이 "confirmed" 상태인지부터 확인해야 한다
(스펙: 임시 상태에서는 직원에게 절대 노출되지 않음).
"""

from sqlmodel import Session, select

from app.models import DEFAULT_STORE_ID, Schedule, ScheduleEntry, Staff, Store
from app.schemas.schedule import PublicRow, PublicScheduleResult


def build_public_view(session: Session, sched: Schedule) -> PublicScheduleResult:
    store = session.get(Store, sched.store_id)
    entries = session.exec(
        select(ScheduleEntry).where(ScheduleEntry.schedule_id == sched.id)
    ).all()

    staff_rows = session.exec(
        select(Staff)
        .where(Staff.store_id == sched.store_id, Staff.is_active == True)  # noqa: E712
        .order_by(Staff.role.desc(), Staff.created_at)
    ).all()

    cells_by_staff: dict[int, dict[str, str]] = {s.id: {} for s in staff_rows}
    day_set: set[str] = set()
    for e in entries:
        d = e.work_date.isoformat()
        day_set.add(d)
        cells_by_staff.setdefault(e.staff_id, {})[d] = e.work_code

    rows = [
        PublicRow(
            staff_name=s.name,
            position=s.position,
            role=s.role,
            cells=cells_by_staff.get(s.id, {}),
        )
        for s in staff_rows
    ]
    return PublicScheduleResult(
        year=sched.year,
        month=sched.month,
        store_name=store.name if store else "우리 식당",
        days=sorted(day_set),
        rows=rows,
        generated_at=sched.created_at,
    )


def get_confirmed_schedule(session: Session, year: int, month: int) -> Schedule | None:
    """이번 달 스케줄이 있고 "공유됨(confirmed)" 상태일 때만 돌려준다."""
    sched = session.exec(
        select(Schedule).where(
            Schedule.store_id == DEFAULT_STORE_ID,
            Schedule.year == year,
            Schedule.month == month,
        )
    ).first()
    if sched is None or sched.status != "confirmed":
        return None
    return sched
