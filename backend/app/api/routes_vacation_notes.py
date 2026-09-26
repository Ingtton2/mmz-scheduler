"""
"휴가 일정 공유" 메모판 API — 순수 참고용 (연차·사전휴무·자동배치와 무관).

  GET /api/me/vacation-notes        (직원) 전체 현황 + 나의 staff_id
  PUT /api/me/vacation-notes/mine   (직원) 내 메모 통째로 저장, 비면 삭제
  GET /api/vacation-notes           (관리자) 전체 현황 조회만

참여 대상은 정직원·점장(has_leave_balance)만 — 파트타임·사장님은 적을 수도 없고
목록에도 안 나온다. staff_id 는 요청 본문이 아니라 로그인 토큰에서만 꺼내므로
다른 사람 메모를 대신 고칠 수 없다.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api import routes_me
from app.api.routes_me import get_current_staff
from app.database import get_session
from app.models import DEFAULT_STORE_ID, MEMO_MAX, PersonalScheduleNote, Staff
from app.models.base import utcnow
from app.schemas.staff import has_leave_balance
from app.schemas.vacation_note import (
    DateRange,
    VacationBoard,
    VacationNoteOut,
    VacationNoteSave,
)
from app.services.vacation_window import window_months

me_router = APIRouter(prefix="/me/vacation-notes", tags=["vacation-notes"])
router = APIRouter(prefix="/vacation-notes", tags=["vacation-notes"])

MAX_RANGES = 40


def _merge(ranges: list[DateRange]) -> list[DateRange]:
    """겹치거나 붙어 있는 구간을 하나로 합친다."""
    out: list[DateRange] = []
    for r in sorted(ranges, key=lambda r: r.start):
        if out and r.start <= out[-1].end + timedelta(days=1):
            if r.end > out[-1].end:
                out[-1] = DateRange(start=out[-1].start, end=r.end)
        else:
            out.append(DateRange(start=r.start, end=r.end))
    return out


def _ym(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


def _to_out(note: PersonalScheduleNote, name: str, window: set[str]) -> VacationNoteOut | None:
    """지난 달 기록은 화면에서 빼고 보여준다 (DB 에는 다음 저장 때 정리됨)."""
    months = sorted(m for m in note.months if m in window)
    ranges = [
        DateRange(start=r["start"], end=r["end"])
        for r in note.ranges
        if r.get("start", "")[:7] in months
    ]
    no_plans = note.no_plans and not months
    if not months and not no_plans and not note.memo:
        return None
    return VacationNoteOut(
        staff_id=note.staff_id,
        name=name,
        months=months,
        ranges=ranges,
        no_plans=no_plans,
        memo=note.memo,
        updated_at=note.updated_at,
    )


def _board(session: Session, today: date) -> VacationBoard:
    months = window_months(today)
    window = set(months)
    rows = session.exec(
        select(PersonalScheduleNote, Staff)
        .join(Staff, Staff.id == PersonalScheduleNote.staff_id)
        .where(
            PersonalScheduleNote.store_id == DEFAULT_STORE_ID,
            Staff.is_active == True,  # noqa: E712
        )
        .order_by(Staff.sort_order, Staff.id)
    ).all()
    notes = [
        out
        for note, staff in rows
        if has_leave_balance(staff.role, staff.employment_type)
        and (out := _to_out(note, staff.name, window)) is not None
    ]
    return VacationBoard(months=months, today=today, notes=notes)


@me_router.get("", response_model=VacationBoard)
def my_board(
    staff: Staff = Depends(get_current_staff), session: Session = Depends(get_session)
) -> VacationBoard:
    board = _board(session, routes_me._today())
    board.my_staff_id = staff.id
    board.my_name = staff.name
    board.can_edit = has_leave_balance(staff.role, staff.employment_type)
    return board


@me_router.put("/mine", response_model=VacationNoteOut | None)
def save_mine(
    body: VacationNoteSave,
    staff: Staff = Depends(get_current_staff),
    session: Session = Depends(get_session),
) -> VacationNoteOut | None:
    if not has_leave_balance(staff.role, staff.employment_type):
        raise HTTPException(status_code=403, detail="정직원·점장만 적을 수 있어요.")

    window = set(window_months(routes_me._today()))
    months = sorted(set(body.months))
    bad = [m for m in months if m not in window]
    if bad:
        raise HTTPException(status_code=400, detail=f"선택할 수 없는 달이에요: {', '.join(bad)}")

    for r in body.ranges:
        if r.start > r.end:
            raise HTTPException(status_code=400, detail="시작일이 종료일보다 늦어요.")
        if _ym(r.start) != _ym(r.end):
            raise HTTPException(status_code=400, detail="기간은 한 달 안에서만 고를 수 있어요.")
        if _ym(r.start) not in months:
            raise HTTPException(status_code=400, detail="기간이 선택한 달 밖에 있어요.")
    ranges = _merge(body.ranges)
    if len(ranges) > MAX_RANGES:
        raise HTTPException(status_code=400, detail=f"기간은 최대 {MAX_RANGES}개까지예요.")

    memo = body.memo.strip()[:MEMO_MAX]
    no_plans = body.no_plans and not months

    note = session.exec(
        select(PersonalScheduleNote).where(PersonalScheduleNote.staff_id == staff.id)
    ).first()

    if not months and not no_plans and not memo:
        if note is not None:
            session.delete(note)
            session.commit()
        return None

    if note is None:
        note = PersonalScheduleNote(store_id=DEFAULT_STORE_ID, staff_id=staff.id)
    note.months = months
    note.ranges = [{"start": r.start.isoformat(), "end": r.end.isoformat()} for r in ranges]
    note.no_plans = no_plans
    note.memo = memo
    note.updated_at = utcnow()
    session.add(note)
    session.commit()
    session.refresh(note)
    return _to_out(note, staff.name, window)


@router.get("", response_model=VacationBoard)
def admin_board(session: Session = Depends(get_session)) -> VacationBoard:
    return _board(session, routes_me._today())
