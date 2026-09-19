"""
연차 신청 기록 조회 API (읽기 전용).

이 식당의 연차는 직원이 날짜를 신청하고 승인하는 방식이 아니다 — 사장님이 연차를 부여하고,
자동배치 실행 때 직원별 사용 개수를 정하면 자동배치가 날짜를 골라 넣는다
(POST /api/schedule/auto 의 leave_days). 예전에 받았던 신청 기록만 조회용으로 남긴다.

  GET /api/leave-requests   (과거) 신청 목록 (직원 이름 포함, 시작일순)
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import DEFAULT_STORE_ID, LeaveRequest, Staff
from app.schemas.leave import LeaveRequestRead

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


@router.get("", response_model=list[LeaveRequestRead])
def list_requests(session: Session = Depends(get_session)) -> list[LeaveRequestRead]:
    rows = session.exec(
        select(LeaveRequest, Staff)
        .join(Staff, Staff.id == LeaveRequest.staff_id)
        .where(LeaveRequest.store_id == DEFAULT_STORE_ID)
        .order_by(LeaveRequest.start_date)
    ).all()
    return [_to_read(req, staff.name) for req, staff in rows]
