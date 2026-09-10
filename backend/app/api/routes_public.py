"""
직원 조회 전용 API (스펙 6.2, 7) — 로그인 없음.

QR 을 스캔하면 프론트가 /schedule/{공유코드} 로 들어오고, 그 화면이
이 API 로 스케줄 데이터를 받아 표(이미지 형태)로 보여준다.

  GET /api/public/schedule/{share_code}  -> 공유된 스케줄 (없으면 404)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Schedule, ScheduleEntry, Staff, Store
from app.schemas.schedule import PublicRow, PublicScheduleResult

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/schedule/{share_code}", response_model=PublicScheduleResult)
def public_schedule(
    share_code: str, session: Session = Depends(get_session)
) -> PublicScheduleResult:
    sched = session.exec(
        select(Schedule).where(Schedule.share_code == share_code)
    ).first()
    if sched is None:
        raise HTTPException(status_code=404, detail="스케줄을 찾을 수 없습니다.")

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
