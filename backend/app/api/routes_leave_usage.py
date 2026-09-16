"""
연차 부여/사용 현황 API ("연차 관리 > 연차 사용 현황" 탭, 스펙 3).

  GET  /api/leave/grant-candidates   이번 달 부여 대상 (신규 입사자 월차, 1주년 연차)
  POST /api/leave/grants             연차 부여 (부여연차 증가 + 부여 이력 기록)
  GET  /api/leave/grant-log          부여 이력 (최신순)
  GET  /api/leave/usage-log          사용 이력 (연차 승인 시 자동 기록, 최신순)
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import DEFAULT_STORE_ID, LeaveBalance, LeaveGrantLog, LeaveUsageLog, Staff
from app.schemas.leave_usage import (
    GrantCandidate,
    LeaveGrantCreate,
    LeaveGrantRead,
    LeaveUsageLogRead,
)
from app.schemas.staff import has_leave_balance
from app.services.leave_anniversary import list_grant_candidates

router = APIRouter(prefix="/leave", tags=["leave-usage"])


@router.get("/grant-candidates", response_model=list[GrantCandidate])
def grant_candidates(session: Session = Depends(get_session)) -> list[GrantCandidate]:
    return [GrantCandidate(**c) for c in list_grant_candidates(session, date.today())]


@router.post("/grants", response_model=LeaveGrantRead, status_code=201)
def create_grant(
    payload: LeaveGrantCreate, session: Session = Depends(get_session)
) -> LeaveGrantRead:
    staff = session.get(Staff, payload.staff_id)
    if staff is None or staff.store_id != DEFAULT_STORE_ID:
        raise HTTPException(status_code=404, detail="해당 직원을 찾을 수 없습니다.")
    if not has_leave_balance(staff.role, staff.employment_type):
        raise HTTPException(status_code=400, detail="연차는 정직원만 부여할 수 있습니다.")

    bal = session.exec(
        select(LeaveBalance).where(LeaveBalance.staff_id == staff.id)
    ).first()
    if bal is None:
        bal = LeaveBalance(store_id=DEFAULT_STORE_ID, staff_id=staff.id)
    bal.granted += payload.days
    session.add(bal)

    log = LeaveGrantLog(
        store_id=DEFAULT_STORE_ID,
        staff_id=staff.id,
        granted_at=payload.granted_at or date.today(),
        days=payload.days,
        note=payload.note,
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return LeaveGrantRead(
        id=log.id,
        staff_id=staff.id,
        staff_name=staff.name,
        granted_at=log.granted_at,
        days=log.days,
        note=log.note,
    )


@router.get("/grant-log", response_model=list[LeaveGrantRead])
def grant_log(session: Session = Depends(get_session)) -> list[LeaveGrantRead]:
    rows = session.exec(
        select(LeaveGrantLog, Staff)
        .join(Staff, Staff.id == LeaveGrantLog.staff_id)
        .where(LeaveGrantLog.store_id == DEFAULT_STORE_ID)
        .order_by(LeaveGrantLog.granted_at.desc(), LeaveGrantLog.id.desc())
    ).all()
    return [
        LeaveGrantRead(
            id=g.id,
            staff_id=g.staff_id,
            staff_name=s.name,
            granted_at=g.granted_at,
            days=g.days,
            note=g.note,
        )
        for g, s in rows
    ]


@router.get("/usage-log", response_model=list[LeaveUsageLogRead])
def usage_log(session: Session = Depends(get_session)) -> list[LeaveUsageLogRead]:
    rows = session.exec(
        select(LeaveUsageLog, Staff)
        .join(Staff, Staff.id == LeaveUsageLog.staff_id)
        .where(LeaveUsageLog.store_id == DEFAULT_STORE_ID)
        .order_by(LeaveUsageLog.created_at.desc())
    ).all()
    return [
        LeaveUsageLogRead(
            id=u.id,
            staff_id=u.staff_id,
            staff_name=s.name,
            start_date=u.start_date,
            end_date=u.end_date,
            days=u.days,
            applied_at=u.applied_at,
            remaining_after=u.remaining_after,
        )
        for u, s in rows
    ]
