"""
자동배치 실행 / 저장 / 수동 수정 / 공유 API (스펙 5, 6.1, 7).

  POST  /api/schedule/auto              { year, month }  -> 자동배치 + 저장 + 결과
  GET   /api/schedule?year=&month=      -> 저장된 스케줄 (없으면 404)
  PATCH /api/schedule/entries           { year, month, changes[] } -> 셀 수동 수정
  POST  /api/schedule/{year}/{month}/share  -> "공유됨(confirmed)" 상태로 전환
"""

import calendar
import secrets
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, delete, select

from app.database import get_session
from app.models import (
    DEFAULT_STORE_ID,
    DayOffRequest,
    LeaveBalance,
    LeaveRequest,
    Schedule,
    ScheduleEntry,
    Staff,
    StaffingRequirement,
    Store,
)
from app.models.base import date_range, utcnow
from app.scheduler.engine import SolveInput, StaffInput, build_schedule
from app.schemas.staff import has_leave_balance
from app.services.schedule_summary import summarize as _summarize
from app.services.schedule_window import can_manual_edit, can_run_auto_schedule
from app.schemas.schedule import (
    VALID_CODES,
    AutoScheduleRequest,
    ManualEditRequest,
    ScheduleResult,
    ScheduleStaffRow,
    ScheduleWarningOut,
    ShareResult,
    ShiftSummary,
)

router = APIRouter(prefix="/schedule", tags=["schedule"])


def _today() -> date:
    """테스트에서 monkeypatch 하기 쉽게 date.today() 를 함수로 감싼다."""
    return date.today()


def _load_active_staff(session: Session) -> list[Staff]:
    return list(
        session.exec(
            select(Staff)
            .where(Staff.store_id == DEFAULT_STORE_ID, Staff.is_active == True)  # noqa: E712
            .order_by(Staff.role == "owner", Staff.sort_order, Staff.created_at)  # 사장님을 아래로
        ).all()
    )


def _load_leave_dates(session: Session) -> dict[int, set[date]]:
    """연차 기간을 날짜 집합으로 펼친다."""
    rows = session.exec(
        select(LeaveRequest).where(LeaveRequest.store_id == DEFAULT_STORE_ID)
    ).all()
    out: dict[int, set[date]] = {}
    for r in rows:
        out.setdefault(r.staff_id, set()).update(date_range(r.start_date, r.end_date))
    return out


def _load_blocked_dates(session: Session) -> dict[int, set[date]]:
    """사전 휴무 신청 기간을 날짜 집합으로 펼친다 (배치 금지, 근무일수는 유지)."""
    rows = session.exec(
        select(DayOffRequest).where(DayOffRequest.store_id == DEFAULT_STORE_ID)
    ).all()
    out: dict[int, set[date]] = {}
    for r in rows:
        out.setdefault(r.staff_id, set()).update(date_range(r.start_date, r.end_date))
    return out


def _load_min_days_off(session: Session) -> dict[int, int]:
    """직원별 월 최소 휴일(기본휴무). leave_balance 에 저장돼 있고 정직원만 존재."""
    rows = session.exec(
        select(LeaveBalance).where(LeaveBalance.store_id == DEFAULT_STORE_ID)
    ).all()
    return {b.staff_id: b.base_off_days for b in rows}


def _load_requirements(session: Session) -> dict[int, dict[str, dict[str, int]]]:
    """weekday -> position -> slot(open/mid/close) -> 최소인원."""
    rows = session.exec(
        select(StaffingRequirement).where(
            StaffingRequirement.store_id == DEFAULT_STORE_ID
        )
    ).all()
    out: dict[int, dict[str, dict[str, int]]] = {}
    for r in rows:
        out.setdefault(r.weekday, {}).setdefault(r.position, {})[r.time_slot] = (
            r.min_headcount
        )
    return out


def _load_daily_headcount_target(session: Session) -> int:
    store = session.get(Store, DEFAULT_STORE_ID)
    return store.daily_headcount_target if store else 0


def _persist(
    session: Session, result_rows: dict[int, dict[str, str]], year: int, month: int
) -> Schedule:
    sched = session.exec(
        select(Schedule).where(
            Schedule.store_id == DEFAULT_STORE_ID,
            Schedule.year == year,
            Schedule.month == month,
        )
    ).first()
    if sched is None:
        sched = Schedule(store_id=DEFAULT_STORE_ID, year=year, month=month, status="draft")
        session.add(sched)
        session.commit()
        session.refresh(sched)
    else:
        session.exec(delete(ScheduleEntry).where(ScheduleEntry.schedule_id == sched.id))

    for staff_id, cells in result_rows.items():
        for day_str, code in cells.items():
            session.add(
                ScheduleEntry(
                    schedule_id=sched.id,
                    staff_id=staff_id,
                    work_date=date.fromisoformat(day_str),
                    work_code=code,
                )
            )
    sched.created_at = utcnow()
    sched.edited = False  # 자동배치를 다시 돌리면 수동 수정본은 덮어써짐
    # 자동배치를 (다시) 돌리면 이전에 공유했더라도 항상 "임시" 상태로 되돌린다 —
    # 사장님이 다시 "공유"를 눌러야 직원들에게 최신본이 보인다.
    sched.status = "draft"
    session.add(sched)
    session.commit()
    return sched


@router.post("/auto", response_model=ScheduleResult)
def run_auto_schedule(
    payload: AutoScheduleRequest, session: Session = Depends(get_session)
) -> ScheduleResult:
    if not can_run_auto_schedule(payload.year, payload.month, _today()):
        raise HTTPException(
            status_code=400,
            detail="이번 달과 그 이전 달은 자동배치를 다시 실행할 수 없습니다. 다음 달 스케줄부터 가능해요.",
        )

    staff_rows = _load_active_staff(session)
    mdo = _load_min_days_off(session)

    inp = SolveInput(
        year=payload.year,
        month=payload.month,
        staff=[
            StaffInput(
                id=s.id,
                name=s.name,
                position=s.position,
                role=s.role,
                work_weekdays=frozenset(
                    int(x) for x in s.work_weekdays.split(",") if x.strip() != ""
                ),
                fixed=s.fixed_schedule,
                is_part_time=s.employment_type == "part_time",
                min_days_off=(
                    mdo.get(s.id, 0)
                    if has_leave_balance(s.role, s.employment_type)
                    else 0
                ),
            )
            for s in staff_rows
        ],
        leave_dates=_load_leave_dates(session),
        blocked_dates=_load_blocked_dates(session),
        requirements=_load_requirements(session),
        daily_headcount_target=_load_daily_headcount_target(session),
    )

    solved = build_schedule(inp)
    sched = _persist(session, solved.entries, payload.year, payload.month)

    rows = [
        ScheduleStaffRow(
            staff_id=s.id,
            staff_name=s.name,
            position=s.position,
            role=s.role,
            employment_type=s.employment_type,
            cells=solved.entries.get(s.id, {}),
            summary=ShiftSummary(**solved.shift_summary.get(s.id, {})),
        )
        for s in staff_rows
    ]

    return ScheduleResult(
        year=solved.year,
        month=solved.month,
        days=solved.days,
        rows=rows,
        warnings=[
            ScheduleWarningOut(
                date=w.date,
                position=w.position,
                needed=w.needed,
                filled=w.filled,
                message=w.message,
            )
            for w in solved.warnings
        ],
        feasible=solved.feasible,
        solve_seconds=solved.solve_seconds,
        saved=True,
        edited=False,
        status=sched.status,
        share_code=sched.share_code,
        generated_at=utcnow(),
    )


def _get_sched(session: Session, year: int, month: int) -> Schedule:
    sched = session.exec(
        select(Schedule).where(
            Schedule.store_id == DEFAULT_STORE_ID,
            Schedule.year == year,
            Schedule.month == month,
        )
    ).first()
    if sched is None:
        raise HTTPException(status_code=404, detail="아직 저장된 스케줄이 없습니다.")
    return sched


def _saved_result(session: Session, sched: Schedule) -> ScheduleResult:
    """저장된 ScheduleEntry 로부터 ScheduleResult 를 만든다 (요약은 셀에서 재계산).

    날짜 칸은 그 달 전체(1일~말일)로 만든다 — 엔트리가 하나도 없는(자동배치를
    아직 안 돌린) 스케줄이어도 표가 비어 보이지 않고 빈 칸을 클릭해서 채울 수
    있어야 하기 때문.
    """
    entries = session.exec(
        select(ScheduleEntry).where(ScheduleEntry.schedule_id == sched.id)
    ).all()
    staff_rows = _load_active_staff(session)
    cells_by_staff: dict[int, dict[str, str]] = {s.id: {} for s in staff_rows}
    for e in entries:
        cells_by_staff.setdefault(e.staff_id, {})[e.work_date.isoformat()] = e.work_code

    last_day = calendar.monthrange(sched.year, sched.month)[1]
    days = [date(sched.year, sched.month, d).isoformat() for d in range(1, last_day + 1)]

    rows = [
        ScheduleStaffRow(
            staff_id=s.id,
            staff_name=s.name,
            position=s.position,
            role=s.role,
            employment_type=s.employment_type,
            cells=cells_by_staff.get(s.id, {}),
            summary=_summarize(cells_by_staff.get(s.id, {})),
        )
        for s in staff_rows
    ]
    return ScheduleResult(
        year=sched.year,
        month=sched.month,
        days=days,
        rows=rows,
        warnings=[],
        feasible=True,
        saved=True,
        edited=sched.edited,
        status=sched.status,
        share_code=sched.share_code,
        generated_at=sched.created_at,
    )


@router.get("", response_model=ScheduleResult)
def get_saved_schedule(
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
    session: Session = Depends(get_session),
) -> ScheduleResult:
    return _saved_result(session, _get_sched(session, year, month))


@router.patch("/entries", response_model=ScheduleResult)
def edit_entries(
    payload: ManualEditRequest, session: Session = Depends(get_session)
) -> ScheduleResult:
    """사장님이 자동배치 결과의 특정 칸(직원×날짜)을 수동으로 바꾼다 (스펙 6.1)."""
    if not can_manual_edit(payload.year, payload.month, _today()):
        raise HTTPException(
            status_code=400, detail="이전 달 스케줄은 더 이상 수정할 수 없습니다."
        )
    sched = _get_sched(session, payload.year, payload.month)

    for ch in payload.changes:
        if ch.work_code not in VALID_CODES:
            raise HTTPException(
                status_code=422, detail=f"허용되지 않는 근무 코드: {ch.work_code}"
            )
        row = session.exec(
            select(ScheduleEntry).where(
                ScheduleEntry.schedule_id == sched.id,
                ScheduleEntry.staff_id == ch.staff_id,
                ScheduleEntry.work_date == ch.work_date,
            )
        ).first()
        if row is None:
            row = ScheduleEntry(
                schedule_id=sched.id,
                staff_id=ch.staff_id,
                work_date=ch.work_date,
                work_code=ch.work_code,
            )
        else:
            row.work_code = ch.work_code
        session.add(row)

    if payload.changes:
        sched.edited = True
        # 공유된 뒤에 또 수정하면 다시 "임시"로 — 사장님이 다시 공유해야 직원에게 보임.
        sched.status = "draft"
        session.add(sched)
    session.commit()
    return _saved_result(session, sched)


@router.post("/{year}/{month}/share", response_model=ShareResult)
def share_schedule(
    year: int, month: int, session: Session = Depends(get_session)
) -> ShareResult:
    """스케줄을 "공유됨(confirmed)" 상태로 바꾼다 — 로그인한 직원에게 노출.

    공유코드는 스케줄을 고유하게 식별해두기 위해 처음 한 번만 발급하고 그 뒤로는
    재사용한다. 상태 전환(draft->confirmed)은 재공유 때도 매번 일어나야 한다
    (수정 후 재공유 흐름)."""
    sched = _get_sched(session, year, month)
    if not sched.share_code:
        sched.share_code = secrets.token_urlsafe(9)
    sched.status = "confirmed"
    session.add(sched)
    session.commit()
    return ShareResult(share_code=sched.share_code)
