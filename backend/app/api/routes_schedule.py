"""
자동배치 실행 / 저장 / 수동 수정 / 공유 API (스펙 5, 6.1, 7).

  POST  /api/schedule/auto              { year, month, leave_days? }  -> 자동배치 + 저장 + 결과
                                        (leave_days: 직원 id -> 이번 달 연차 개수, 날짜는 엔진이 랜덤 배정 + 사용연차 차감)
  GET   /api/schedule/leave-plan?year=&month=  -> 직원별 사용 가능 잔여연차 + 저장된 개수
  GET   /api/schedule?year=&month=      -> 저장된 스케줄 (없으면 404)
  PATCH /api/schedule/entries           { year, month, changes[] } -> 셀 수동 수정
  POST  /api/schedule/{year}/{month}/share  -> "공유됨(confirmed)" 상태로 전환
"""

import calendar
import secrets
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, delete, select

from app.api.routes_kitchen_rotation import get_or_compute_rotation
from app.database import get_session
from app.models import (
    DEFAULT_STORE_ID,
    DayOffRequest,
    Holiday,
    LeaveBalance,
    MonthlyLeavePlan,
    Schedule,
    ScheduleEntry,
    Staff,
    StaffingRequirement,
    Store,
)
from app.models.base import date_range, utcnow
from app.scheduler.engine import SolveInput, StaffInput, build_schedule
from app.schemas.staff import has_leave_balance
from app.services.headcount_check import check_headcount
from app.services.schedule_summary import summarize as _summarize
from app.services.schedule_window import can_manual_edit, can_run_auto_schedule
from app.schemas.schedule import (
    VALID_CODES,
    AutoScheduleRequest,
    ManualEditRequest,
    ScheduleResult,
    LeavePlanRow,
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


def _load_holiday_dates(session: Session, year: int, month: int) -> set[date]:
    """그 달에 등록된 공휴일 날짜 집합 (정직원·점장 휴무 공정성 계산용)."""
    rows = session.exec(
        select(Holiday).where(Holiday.store_id == DEFAULT_STORE_ID)
    ).all()
    return {r.date for r in rows if r.date.year == year and r.date.month == month}


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


def _leave_eligible(s: Staff) -> bool:
    return has_leave_balance(s.role, s.employment_type)


def _balance_of(session: Session, staff_id: int) -> LeaveBalance | None:
    return session.exec(
        select(LeaveBalance).where(LeaveBalance.staff_id == staff_id)
    ).first()


def _plan_of(session: Session, staff_id: int, year: int, month: int) -> MonthlyLeavePlan | None:
    return session.exec(
        select(MonthlyLeavePlan).where(
            MonthlyLeavePlan.store_id == DEFAULT_STORE_ID,
            MonthlyLeavePlan.staff_id == staff_id,
            MonthlyLeavePlan.year == year,
            MonthlyLeavePlan.month == month,
        )
    ).first()


def _available_leave(session: Session, s: Staff, year: int, month: int) -> tuple[float, int]:
    """(이번 달에 쓸 수 있는 잔여연차, 이 달에 이미 저장/차감된 개수).
    이 달에 이미 차감된 분은 다시 돌릴 때 되돌려지므로 잔여에 더해서 계산한다."""
    bal = _balance_of(session, s.id)
    plan = _plan_of(session, s.id, year, month)
    saved = plan.days if plan else 0
    remaining = (bal.granted - bal.used) if bal else 0.0
    return remaining + saved, saved


def _validate_leave_days(
    session: Session, staff_rows: list[Staff], year: int, month: int, leave_days: dict[int, int]
) -> dict[int, int]:
    by_id = {s.id: s for s in staff_rows}
    out: dict[int, int] = {}
    for sid, days in leave_days.items():
        if days < 0:
            raise HTTPException(status_code=422, detail="연차 개수는 0 이상이어야 합니다.")
        if days == 0:
            continue
        s = by_id.get(sid)
        if s is None:
            raise HTTPException(status_code=422, detail="해당 직원을 찾을 수 없습니다.")
        if not _leave_eligible(s):
            raise HTTPException(
                status_code=422, detail=f"{s.name}: 연차는 정직원·점장만 사용할 수 있습니다."
            )
        available, _ = _available_leave(session, s, year, month)
        if days > available:
            raise HTTPException(
                status_code=422,
                detail=f"{s.name}: 잔여연차({available:g}개)보다 많이 지정했습니다.",
            )
        out[sid] = days
    return out


def _apply_leave_plan(
    session: Session, staff_rows: list[Staff], year: int, month: int, placed: dict[int, int]
) -> None:
    """실제 배치된 연차 개수를 사용연차에서 차감한다. 이 달에 이미 차감된 분은 먼저
    되돌린 것과 같은 효과라서(차이만큼만 가감) 다시 돌려도 중복 차감되지 않는다."""
    for s in staff_rows:
        if not _leave_eligible(s):
            continue
        new = placed.get(s.id, 0)
        plan = _plan_of(session, s.id, year, month)
        prev = plan.days if plan else 0
        if new == prev and plan is not None:
            continue
        bal = _balance_of(session, s.id)
        if bal is None:
            bal = LeaveBalance(store_id=DEFAULT_STORE_ID, staff_id=s.id)
        bal.used = round(bal.used + new - prev, 2)
        session.add(bal)
        remaining_after = round(bal.granted - bal.used, 2)
        if plan is None:
            if new == 0:
                continue
            plan = MonthlyLeavePlan(
                store_id=DEFAULT_STORE_ID, staff_id=s.id, year=year, month=month,
                days=new, remaining_after=remaining_after,
            )
        else:
            plan.days = new
            plan.remaining_after = remaining_after
            plan.applied_at = date.today()
        session.add(plan)


@router.get("/leave-plan", response_model=list[LeavePlanRow])
def get_leave_plan(
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
    session: Session = Depends(get_session),
) -> list[LeavePlanRow]:
    """자동배치 화면의 연차 입력 패널용: 직원별 사용 가능한 잔여연차 + 이 달에 저장된 개수."""
    rows = []
    for s in _load_active_staff(session):
        if not _leave_eligible(s):
            continue
        available, saved = _available_leave(session, s, year, month)
        rows.append(
            LeavePlanRow(
                staff_id=s.id, staff_name=s.name, remaining=round(available, 2), saved_days=saved
            )
        )
    return rows


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
    rotation = get_or_compute_rotation(session, payload.year, payload.month)
    leave_counts = _validate_leave_days(
        session, staff_rows, payload.year, payload.month, payload.leave_days
    )

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
                rotation_slot=rotation.get(s.id),
                close_backup=s.close_backup,
            )
            for s in staff_rows
        ],
        leave_counts=leave_counts,
        blocked_dates=_load_blocked_dates(session),
        holiday_dates=_load_holiday_dates(session, payload.year, payload.month),
        requirements=_load_requirements(session),
        daily_headcount_target=_load_daily_headcount_target(session),
    )

    solved = build_schedule(inp)
    if any(solved.entries.get(s.id) for s in staff_rows):  # 해를 못 찾았으면 차감하지 않음
        _apply_leave_plan(session, staff_rows, payload.year, payload.month, solved.leave_placed)
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
        published_at=sched.published_at,
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

    # 엔진을 다시 돌리지 않는 경우(다시 열기/수동 수정)에도 인원 부족·초과 경고를 다시 계산
    warnings = check_headcount(
        days,
        {s.id: cells_by_staff.get(s.id, {}) for s in staff_rows},
        {s.id: s.position for s in staff_rows if s.employment_type == "part_time"},
        _load_requirements(session),
        _load_daily_headcount_target(session),
    )

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
        warnings=warnings,
        feasible=not warnings,
        saved=True,
        edited=sched.edited,
        status=sched.status,
        share_code=sched.share_code,
        published_at=sched.published_at,
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
    sched.published_at = utcnow()
    session.add(sched)
    session.commit()
    return ShareResult(share_code=sched.share_code, published_at=sched.published_at)
