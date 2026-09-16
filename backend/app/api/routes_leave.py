"""
연차 신청 API (스펙 3).

지금은 직원이 직접 신청하는 화면 대신, 사장님이 대신 입력하는 방식.
신청은 기간(시작일~종료일) 단위. 자동배치에서 '최우선 고정'으로 쓰인다.

  GET    /api/leave-requests        신청 목록 (직원 이름 포함, 시작일순)
  POST   /api/leave-requests        신청 추가 (기간 겹치면 거부)
  PATCH  /api/leave-requests/{id}   상태 변경(신청<->확정) 등 수정
  DELETE /api/leave-requests/{id}   신청 삭제
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import DEFAULT_STORE_ID, LeaveRequest, Staff
from app.schemas.leave import LeaveRequestCreate, LeaveRequestRead, LeaveRequestUpdate
from app.services import leave_usage
from app.services.date_overlap import overlaps as _overlaps

router = APIRouter(prefix="/leave-requests", tags=["leave-requests"])


def _days(start: date, end: date) -> int:
    return (end - start).days + 1


def _to_read(req: LeaveRequest, staff_name: str) -> LeaveRequestRead:
    return LeaveRequestRead(
        id=req.id,
        staff_id=req.staff_id,
        staff_name=staff_name,
        start_date=req.start_date,
        end_date=req.end_date,
        days=_days(req.start_date, req.end_date),
        applied_at=req.applied_at,
        status=req.status,
        note=req.note,
        created_at=req.created_at,
    )


def _staff_or_404(session: Session, staff_id: int) -> Staff:
    staff = session.get(Staff, staff_id)
    if staff is None or staff.store_id != DEFAULT_STORE_ID:
        raise HTTPException(status_code=404, detail="해당 직원을 찾을 수 없습니다.")
    return staff


@router.get("", response_model=list[LeaveRequestRead])
def list_requests(session: Session = Depends(get_session)) -> list[LeaveRequestRead]:
    rows = session.exec(
        select(LeaveRequest, Staff)
        .join(Staff, Staff.id == LeaveRequest.staff_id)
        .where(LeaveRequest.store_id == DEFAULT_STORE_ID)
        .order_by(LeaveRequest.start_date)
    ).all()
    return [_to_read(req, staff.name) for req, staff in rows]


@router.post("", response_model=LeaveRequestRead, status_code=201)
def create_request(
    payload: LeaveRequestCreate, session: Session = Depends(get_session)
) -> LeaveRequestRead:
    staff = _staff_or_404(session, payload.staff_id)

    existing = session.exec(
        select(LeaveRequest).where(
            LeaveRequest.store_id == DEFAULT_STORE_ID,
            LeaveRequest.staff_id == payload.staff_id,
        )
    ).all()
    if any(
        _overlaps(payload.start_date, payload.end_date, r.start_date, r.end_date)
        for r in existing
    ):
        raise HTTPException(status_code=409, detail="이미 신청한 기간과 겹칩니다.")

    req = LeaveRequest(
        store_id=DEFAULT_STORE_ID,
        staff_id=payload.staff_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        applied_at=payload.applied_at or date.today(),
        status=payload.status.value,
        note=(payload.note or None),
    )
    session.add(req)
    session.commit()
    session.refresh(req)

    if req.status == "confirmed":
        leave_usage.sync_on_status_change(
            session, req, old_status="requested", old_start=req.start_date, old_end=req.end_date
        )
        session.commit()
        session.refresh(req)

    return _to_read(req, staff.name)


@router.patch("/{request_id}", response_model=LeaveRequestRead)
def update_request(
    request_id: int, payload: LeaveRequestUpdate, session: Session = Depends(get_session)
) -> LeaveRequestRead:
    req = session.get(LeaveRequest, request_id)
    if req is None or req.store_id != DEFAULT_STORE_ID:
        raise HTTPException(status_code=404, detail="해당 신청을 찾을 수 없습니다.")

    old_status = req.status
    old_start, old_end = req.start_date, req.end_date

    if payload.status is not None:
        req.status = payload.status.value
    if payload.start_date is not None:
        req.start_date = payload.start_date
    if payload.end_date is not None:
        req.end_date = payload.end_date
    if payload.applied_at is not None:
        req.applied_at = payload.applied_at
    if payload.note is not None:
        req.note = payload.note or None
    if req.end_date < req.start_date:
        raise HTTPException(status_code=422, detail="종료일이 시작일보다 빠릅니다.")

    leave_usage.sync_on_status_change(session, req, old_status, old_start, old_end)

    session.add(req)
    session.commit()
    session.refresh(req)

    staff = session.get(Staff, req.staff_id)
    return _to_read(req, staff.name if staff else "(삭제된 직원)")


@router.delete("/{request_id}", status_code=204)
def delete_request(request_id: int, session: Session = Depends(get_session)) -> None:
    req = session.get(LeaveRequest, request_id)
    if req is None or req.store_id != DEFAULT_STORE_ID:
        raise HTTPException(status_code=404, detail="해당 신청을 찾을 수 없습니다.")
    leave_usage.reverse_on_delete(session, req)
    session.delete(req)
    session.commit()
