"""
관리자용: 직원 셀프서비스 계정 승인/거절/PIN 초기화 (스펙 9-2, 9-3).
경로가 /api/public/... 이 아니라서 관리자 로그인이 켜져 있으면 자동으로 보호된다.

  GET  /api/staff-accounts                     계정 전체 목록 (대기중 + 승인됨, 삭제된 직원 제외)
  GET  /api/staff-accounts/pending              승인 대기 목록만 (삭제된 직원 제외)
  POST /api/staff-accounts/{id}/approve         승인
  POST /api/staff-accounts/{id}/reject          거절 (행 삭제 -> 재신청 가능)
  POST /api/staff-accounts/reset-pin/{staff_id}  PIN 초기화 (임시 PIN 발급)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import DEFAULT_STORE_ID, Staff, StaffAccount
from app.models.base import utcnow
from app.schemas.staff_account import AccountOut, PendingAccountOut, ResetPinResult
from app.services import pin as pin_service

router = APIRouter(prefix="/staff-accounts", tags=["staff-accounts"])


def _account_or_404(session: Session, account_id: int) -> StaffAccount:
    acc = session.get(StaffAccount, account_id)
    if acc is None or acc.store_id != DEFAULT_STORE_ID:
        raise HTTPException(status_code=404, detail="해당 계정 신청을 찾을 수 없습니다.")
    return acc


@router.get("", response_model=list[AccountOut])
def list_accounts(session: Session = Depends(get_session)) -> list[AccountOut]:
    rows = session.exec(
        select(StaffAccount, Staff)
        .join(Staff, Staff.id == StaffAccount.staff_id)
        .where(
            StaffAccount.store_id == DEFAULT_STORE_ID,
            Staff.is_active == True,  # noqa: E712
        )
        .order_by(StaffAccount.created_at)
    ).all()
    return [
        AccountOut(
            account_id=acc.id,
            staff_id=acc.staff_id,
            staff_name=staff.name,
            status=acc.status,
            must_change_pin=acc.must_change_pin,
            created_at=acc.created_at,
            approved_at=acc.approved_at,
        )
        for acc, staff in rows
    ]


@router.get("/pending", response_model=list[PendingAccountOut])
def list_pending(session: Session = Depends(get_session)) -> list[PendingAccountOut]:
    rows = session.exec(
        select(StaffAccount, Staff)
        .join(Staff, Staff.id == StaffAccount.staff_id)
        .where(
            StaffAccount.store_id == DEFAULT_STORE_ID,
            StaffAccount.status == "pending",
            Staff.is_active == True,  # noqa: E712
        )
        .order_by(StaffAccount.created_at)
    ).all()
    return [
        PendingAccountOut(
            account_id=acc.id,
            staff_id=acc.staff_id,
            staff_name=staff.name,
            position=staff.position,
            role=staff.role,
            created_at=acc.created_at,
        )
        for acc, staff in rows
    ]


@router.post("/{account_id}/approve", response_model=AccountOut)
def approve(account_id: int, session: Session = Depends(get_session)) -> AccountOut:
    acc = _account_or_404(session, account_id)
    acc.status = "approved"
    acc.approved_at = utcnow()
    session.add(acc)
    session.commit()
    session.refresh(acc)
    staff = session.get(Staff, acc.staff_id)
    return AccountOut(
        account_id=acc.id,
        staff_id=acc.staff_id,
        staff_name=staff.name if staff else "(삭제된 직원)",
        status=acc.status,
        must_change_pin=acc.must_change_pin,
        created_at=acc.created_at,
        approved_at=acc.approved_at,
    )


@router.post("/{account_id}/reject", status_code=204)
def reject(account_id: int, session: Session = Depends(get_session)) -> None:
    acc = _account_or_404(session, account_id)
    session.delete(acc)
    session.commit()


@router.post("/reset-pin/{staff_id}", response_model=ResetPinResult)
def reset_pin(staff_id: int, session: Session = Depends(get_session)) -> ResetPinResult:
    acc = session.exec(
        select(StaffAccount).where(
            StaffAccount.store_id == DEFAULT_STORE_ID, StaffAccount.staff_id == staff_id
        )
    ).first()
    if acc is None:
        raise HTTPException(status_code=404, detail="아직 가입 신청한 적 없는 직원입니다.")

    temp = pin_service.random_pin()
    acc.pin_hash = pin_service.hash_pin(temp)
    acc.must_change_pin = True
    session.add(acc)
    session.commit()
    return ResetPinResult(temp_pin=temp)
