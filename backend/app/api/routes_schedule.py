"""
자동배치 실행 / 저장 / 수동 수정 / 공유 API (스펙 5, 6.1, 7).

  POST  /api/schedule/auto              { year, month }  -> 자동배치 + 저장 + 결과
  GET   /api/schedule?year=&month=      -> 저장된 스케줄 (없으면 404)
  PATCH /api/schedule/entries           { year, month, changes[] } -> 셀 수동 수정
  POST  /api/schedule/{year}/{month}/share  -> 공유 URL/QR 발급
  GET   /api/schedule/share/{code}/qr   -> QR PNG
"""

import io
import secrets
from datetime import date

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, delete, select

from app.config import settings
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

# 코드 -> (슬롯 키, 포지션 키 or None)
_CODE_TO_KEY: dict[str, tuple[str, str | None]] = {
    "FO": ("open", "hall"),
    "FC": ("close", "hall"),
    "BO": ("open", "kitchen"),
    "BM": ("mid", "kitchen"),
    "BC": ("close", "kitchen"),
    "풀오마": ("full", None),
    "D/O": ("off", None),
    "연차": ("leave", None),
    "사휴": ("blocked", None),
    # 구버전 저장분 호환
    "O": ("open", None),
    "M": ("mid", None),
    "C": ("close", None),
}


def _summarize(cells: dict[str, str]) -> ShiftSummary:
    acc = {
        k: 0
        for k in ("open", "mid", "close", "full", "hall", "kitchen", "off", "leave", "blocked")
    }
    for code in cells.values():
        info = _CODE_TO_KEY.get(code)
        if not info:
            continue
        acc[info[0]] += 1
        if info[1]:
            acc[info[1]] += 1
    return ShiftSummary(
        work=acc["open"] + acc["mid"] + acc["close"] + acc["full"], **acc
    )

router = APIRouter(prefix="/schedule", tags=["schedule"])


def _load_active_staff(session: Session) -> list[Staff]:
    return list(
        session.exec(
            select(Staff)
            .where(Staff.store_id == DEFAULT_STORE_ID, Staff.is_active == True)  # noqa: E712
            .order_by(Staff.role.desc(), Staff.created_at)  # 사장님을 위로
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
    session.add(sched)
    session.commit()
    return sched


@router.post("/auto", response_model=ScheduleResult)
def run_auto_schedule(
    payload: AutoScheduleRequest, session: Session = Depends(get_session)
) -> ScheduleResult:
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
    """저장된 ScheduleEntry 로부터 ScheduleResult 를 만든다 (요약은 셀에서 재계산)."""
    entries = session.exec(
        select(ScheduleEntry).where(ScheduleEntry.schedule_id == sched.id)
    ).all()
    staff_rows = _load_active_staff(session)
    cells_by_staff: dict[int, dict[str, str]] = {s.id: {} for s in staff_rows}
    day_set: set[str] = set()
    for e in entries:
        day_str = e.work_date.isoformat()
        day_set.add(day_str)
        cells_by_staff.setdefault(e.staff_id, {})[day_str] = e.work_code

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
        days=sorted(day_set),
        rows=rows,
        warnings=[],
        feasible=True,
        saved=True,
        edited=sched.edited,
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
        session.add(sched)
    session.commit()
    return _saved_result(session, sched)


@router.post("/{year}/{month}/share", response_model=ShareResult)
def share_schedule(
    year: int, month: int, session: Session = Depends(get_session)
) -> ShareResult:
    """완성된 스케줄에 고유 공유코드를 붙이고 URL/QR 경로를 돌려준다 (스펙 7)."""
    sched = _get_sched(session, year, month)
    if not sched.share_code:
        sched.share_code = secrets.token_urlsafe(9)
        sched.status = "confirmed"
        session.add(sched)
        session.commit()
    base = settings.public_base_url.rstrip("/")
    return ShareResult(
        share_code=sched.share_code,
        url=f"{base}/schedule/{sched.share_code}",
        qr_path=f"/api/schedule/share/{sched.share_code}/qr",
    )


@router.get("/share/{code}/qr")
def share_qr(code: str, session: Session = Depends(get_session)) -> Response:
    sched = session.exec(
        select(Schedule).where(Schedule.share_code == code)
    ).first()
    if sched is None:
        raise HTTPException(status_code=404, detail="공유 코드를 찾을 수 없습니다.")
    base = settings.public_base_url.rstrip("/")
    img = qrcode.make(f"{base}/schedule/{code}")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")
