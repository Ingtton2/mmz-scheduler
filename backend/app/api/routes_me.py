"""
직원 셀프서비스 "내 정보" API (스펙 9-4, 9-5) — 로그인한 본인만 조회/신청 가능.

main.py 의 admin_auth 미들웨어는 "/api/me" 를 건드리지 않고 그냥 통과시킨다
(관리자 토큰이 아니라 직원 토큰이 필요하므로). 대신 여기 get_current_staff 가
Authorization: Bearer <직원 토큰> 을 직접 검증한다.

  GET    /api/me                        내 정보 (+ 정직원·점장은 연차 잔액 포함)
  POST   /api/me/change-pin             PIN 변경
  GET    /api/me/leave-requests         내 연차 신청 목록
  POST   /api/me/leave-requests         내 연차 신청 (다음달만, 20일 17시까지 — 스펙 9-5)
  DELETE /api/me/leave-requests/{id}    내 연차 신청 취소 (대기 중인 것만)
  GET    /api/me/holidays               관리자가 등록한 공휴일 (달력 표시용)
  GET    /api/me/leave-grants           내 연차 부여 이력 (최신순)
  GET    /api/me/leave-usages           내 연차 사용 이력 (최신순)
  GET    /api/me/dayoff-requests        내 사전휴무 신청 목록
  POST /api/me/dayoff-requests        내 사전휴무 신청 (다음달만, 20일 17시까지, 월 20일 한도)
  GET  /api/me/schedule/{year}/{month}       내 스케줄만 (공유된 스케줄만 — 임시면 404)
  GET  /api/me/team-schedule/{year}/{month}  이번 달 전체 직원 스케줄 (공유된 것만)
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    MAX_PER_MONTH,
    DEFAULT_STORE_ID,
    DayOffRequest,
    Holiday,
    LeaveBalance,
    LeaveGrantLog,
    LeaveRequest,
    Schedule,
    ScheduleEntry,
    Staff,
    StaffAccount,
)
from app.schemas.holiday import HolidayItem
from app.schemas.leave import LeaveBalanceRead
from app.schemas.leave_usage import LeaveGrantRead, LeaveUsageLogRead
from app.schemas.me import MyDayOffRequestOut, MyLeaveRequestOut, MyRequestCreate, MyScheduleResult
from app.schemas.schedule import PublicScheduleResult
from app.schemas.staff import has_leave_balance
from app.schemas.staff_account import ChangePinRequest, MeOut
from app.services import pin as pin_service
from app.services import staff_tokens
from app.services.date_overlap import days_by_month, overlaps
from app.services.leave_usage_log import build_usage_log
from app.services.request_window import check_window, kst_now
from app.services.schedule_summary import summarize
from app.services.schedule_view import build_public_view, get_confirmed_schedule

router = APIRouter(prefix="/me", tags=["me"])


def _now() -> datetime:
    """한국시간 현재 시각 (서버는 UTC 라서 마감 판단은 KST 로 한다)."""
    return kst_now()


def _today() -> date:
    """테스트에서 monkeypatch 하기 쉽게 오늘 날짜(KST)를 함수로 감싼다."""
    return _now().date()


def get_current_staff(
    authorization: str = Header(default=""), session: Session = Depends(get_session)
) -> Staff:
    token = authorization[len("Bearer ") :] if authorization.startswith("Bearer ") else ""
    staff_id = staff_tokens.verify_token(token)
    if staff_id is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    staff = session.get(Staff, staff_id)
    if staff is None or not staff.is_active or staff.store_id != DEFAULT_STORE_ID:
        raise HTTPException(status_code=401, detail="계정을 찾을 수 없습니다.")
    return staff


def _get_account(session: Session, staff_id: int) -> StaffAccount | None:
    return session.exec(
        select(StaffAccount).where(StaffAccount.staff_id == staff_id)
    ).first()


def _get_leave(session: Session, staff: Staff) -> LeaveBalanceRead | None:
    if not has_leave_balance(staff.role, staff.employment_type):
        return None
    bal = session.exec(
        select(LeaveBalance).where(LeaveBalance.staff_id == staff.id)
    ).first()
    if bal is None:
        return None
    return LeaveBalanceRead.from_values(
        base_off_days=bal.base_off_days,
        granted=bal.granted,
        used=bal.used,
    )


@router.get("", response_model=MeOut)
def me(
    staff: Staff = Depends(get_current_staff), session: Session = Depends(get_session)
) -> MeOut:
    acc = _get_account(session, staff.id)
    return MeOut(
        id=staff.id,
        name=staff.name,
        role=staff.role,
        position=staff.position,
        employment_type=staff.employment_type,
        must_change_pin=acc.must_change_pin if acc else False,
        leave=_get_leave(session, staff),
    )


@router.post("/change-pin")
def change_pin(
    payload: ChangePinRequest,
    staff: Staff = Depends(get_current_staff),
    session: Session = Depends(get_session),
) -> dict:
    acc = _get_account(session, staff.id)
    if acc is None:
        raise HTTPException(status_code=404, detail="계정 정보를 찾을 수 없습니다.")
    if not pin_service.verify_pin(payload.current_pin, acc.pin_hash):
        raise HTTPException(status_code=401, detail="현재 PIN이 올바르지 않습니다.")
    acc.pin_hash = pin_service.hash_pin(payload.new_pin)
    acc.must_change_pin = False
    session.add(acc)
    session.commit()
    return {"ok": True}


def _check_not_part_time(staff: Staff, kind: str) -> None:
    if staff.employment_type == "part_time":
        raise HTTPException(status_code=400, detail=f"파트타임은 {kind} 대상이 아닙니다.")


# --- 연차 ---------------------------------------------------------------


@router.get("/leave-requests", response_model=list[MyLeaveRequestOut])
def my_leave_requests(
    staff: Staff = Depends(get_current_staff), session: Session = Depends(get_session)
) -> list[MyLeaveRequestOut]:
    rows = session.exec(
        select(LeaveRequest)
        .where(LeaveRequest.staff_id == staff.id)
        .order_by(LeaveRequest.start_date)
    ).all()
    return [
        MyLeaveRequestOut(
            id=r.id,
            start_date=r.start_date,
            end_date=r.end_date,
            days=(r.end_date - r.start_date).days + 1,
            applied_at=r.applied_at,
            status=r.status,
            note=r.note,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/leave-grants", response_model=list[LeaveGrantRead])
def my_leave_grants(
    staff: Staff = Depends(get_current_staff), session: Session = Depends(get_session)
) -> list[LeaveGrantRead]:
    rows = session.exec(
        select(LeaveGrantLog)
        .where(LeaveGrantLog.staff_id == staff.id)
        .order_by(LeaveGrantLog.granted_at.desc(), LeaveGrantLog.id.desc())
    ).all()
    return [
        LeaveGrantRead(
            id=g.id,
            staff_id=staff.id,
            staff_name=staff.name,
            granted_at=g.granted_at,
            days=g.days,
            note=g.note,
        )
        for g in rows
    ]


@router.get("/leave-usages", response_model=list[LeaveUsageLogRead])
def my_leave_usages(
    staff: Staff = Depends(get_current_staff), session: Session = Depends(get_session)
) -> list[LeaveUsageLogRead]:
    return build_usage_log(session, staff_id=staff.id)


# --- 사전 휴무 ------------------------------------------------------------


@router.get("/dayoff-requests", response_model=list[MyDayOffRequestOut])
def my_dayoff_requests(
    staff: Staff = Depends(get_current_staff), session: Session = Depends(get_session)
) -> list[MyDayOffRequestOut]:
    rows = session.exec(
        select(DayOffRequest)
        .where(DayOffRequest.staff_id == staff.id)
        .order_by(DayOffRequest.start_date)
    ).all()
    return [
        MyDayOffRequestOut(
            id=r.id,
            start_date=r.start_date,
            end_date=r.end_date,
            days=(r.end_date - r.start_date).days + 1,
            status=r.status,
            reject_reason=r.reject_reason,
            note=r.note,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/dayoff-requests", response_model=MyDayOffRequestOut, status_code=201)
def create_my_dayoff(
    payload: MyRequestCreate,
    staff: Staff = Depends(get_current_staff),
    session: Session = Depends(get_session),
) -> MyDayOffRequestOut:
    _check_not_part_time(staff, "사전 휴무 신청")
    try:
        check_window(payload.start_date, payload.end_date, _today(), _now().time())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    existing = session.exec(
        select(DayOffRequest).where(DayOffRequest.staff_id == staff.id)
    ).all()
    if any(
        overlaps(payload.start_date, payload.end_date, r.start_date, r.end_date)
        for r in existing
    ):
        raise HTTPException(status_code=409, detail="이미 신청한 기간과 겹칩니다.")

    new_by_month = days_by_month(payload.start_date, payload.end_date)
    exist_by_month: dict[tuple[int, int], int] = {}
    for r in existing:
        for ym, cnt in days_by_month(r.start_date, r.end_date).items():
            exist_by_month[ym] = exist_by_month.get(ym, 0) + cnt
    for ym, cnt in new_by_month.items():
        if exist_by_month.get(ym, 0) + cnt > MAX_PER_MONTH:
            raise HTTPException(
                status_code=422,
                detail=f"사전 휴무 신청은 한 달 최대 {MAX_PER_MONTH}일까지입니다.",
            )

    req = DayOffRequest(
        store_id=DEFAULT_STORE_ID,
        staff_id=staff.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        note=(payload.note or None),
    )
    session.add(req)
    session.commit()
    session.refresh(req)
    return MyDayOffRequestOut(
        id=req.id,
        start_date=req.start_date,
        end_date=req.end_date,
        days=(req.end_date - req.start_date).days + 1,
        status=req.status,
        reject_reason=req.reject_reason,
        note=req.note,
        created_at=req.created_at,
    )


# --- 공휴일 (표시 전용) ---------------------------------------------------


@router.get("/holidays", response_model=list[HolidayItem])
def my_holidays(
    staff: Staff = Depends(get_current_staff),  # noqa: ARG001 — 로그인만 확인하면 됨
    session: Session = Depends(get_session),
) -> list[HolidayItem]:
    rows = session.exec(
        select(Holiday).where(Holiday.store_id == DEFAULT_STORE_ID).order_by(Holiday.date)
    ).all()
    return [HolidayItem(id=r.id, date=r.date, name=r.name) for r in rows]


# --- 내 스케줄 -------------------------------------------------------------


@router.get("/schedule/{year}/{month}", response_model=MyScheduleResult)
def my_schedule(
    year: int,
    month: int,
    staff: Staff = Depends(get_current_staff),
    session: Session = Depends(get_session),
) -> MyScheduleResult:
    sched = get_confirmed_schedule(session, year, month, today=_today())
    if sched is None:
        raise HTTPException(status_code=404, detail="아직 스케줄이 공유되지 않았습니다.")

    entries = session.exec(
        select(ScheduleEntry).where(
            ScheduleEntry.schedule_id == sched.id, ScheduleEntry.staff_id == staff.id
        )
    ).all()
    cells = {e.work_date.isoformat(): e.work_code for e in entries}
    return MyScheduleResult(
        year=sched.year,
        month=sched.month,
        days=sorted(cells.keys()),
        cells=cells,
        summary=summarize(cells),
        generated_at=sched.created_at,
    )


@router.get("/team-schedule/{year}/{month}", response_model=PublicScheduleResult)
def my_team_schedule(
    year: int,
    month: int,
    staff: Staff = Depends(get_current_staff),  # noqa: ARG001 — 로그인만 확인하면 됨
    session: Session = Depends(get_session),
) -> PublicScheduleResult:
    """동료 근무일 확인/대타 부탁용 — 이번 달 전체 직원 스케줄 (공유된 것만)."""
    sched = get_confirmed_schedule(session, year, month, today=_today())
    if sched is None:
        raise HTTPException(status_code=404, detail="아직 스케줄이 공유되지 않았습니다.")
    return build_public_view(session, sched)
