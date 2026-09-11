"""
직원 셀프서비스 가입/로그인 (스펙 9) — 로그인 없이 접근 (QR/링크로 /join, /staff-login).

  GET  /api/public/staff-accounts/available    가입 신청 화면 드롭다운 (계정 없는 직원, 사장님 제외)
  POST /api/public/staff-accounts/signup       가입 신청 (기존 직원 선택 + PIN) — 사장님은 대상 아님
                                                (사장님은 관리자 화면을 그대로 쓰므로 셀프 계정 불필요)
  GET  /api/public/staff-accounts/login-list   로그인 화면 드롭다운 (승인된 직원)
  POST /api/public/staff-accounts/login        로그인 (이름 선택 + PIN) -> 토큰 발급
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import DEFAULT_STORE_ID, Staff, StaffAccount
from app.schemas.staff_account import (
    AvailableStaffOut,
    LoginableStaffOut,
    LoginRequest,
    LoginResult,
    MeOut,
    SignupRequest,
    SignupResult,
)
from app.services import pin as pin_service
from app.services import staff_tokens

router = APIRouter(prefix="/public/staff-accounts", tags=["public-accounts"])


@router.get("/available", response_model=list[AvailableStaffOut])
def available(session: Session = Depends(get_session)) -> list[AvailableStaffOut]:
    linked_ids = set(
        session.exec(
            select(StaffAccount.staff_id).where(StaffAccount.store_id == DEFAULT_STORE_ID)
        ).all()
    )
    staff_rows = session.exec(
        select(Staff)
        .where(Staff.store_id == DEFAULT_STORE_ID, Staff.is_active == True)  # noqa: E712
        .order_by(Staff.created_at)
    ).all()
    return [
        AvailableStaffOut(id=s.id, name=s.name, position=s.position, role=s.role)
        for s in staff_rows
        # 사장님은 이 공개 목록에 안 보이게 한다 (직원 화면에서 사장님 이름 노출 방지).
        # 사장님 본인 계정은 관리자 화면(/admin/accounts)에서 따로 만든다.
        if s.id not in linked_ids and s.role != "owner"
    ]


@router.post("/signup", response_model=SignupResult, status_code=201)
def signup(payload: SignupRequest, session: Session = Depends(get_session)) -> SignupResult:
    staff = session.get(Staff, payload.staff_id)
    if staff is None or staff.store_id != DEFAULT_STORE_ID or not staff.is_active:
        raise HTTPException(status_code=404, detail="해당 직원을 찾을 수 없습니다.")
    if staff.role == "owner":
        # 사장님은 관리자 화면을 그대로 쓰므로 셀프서비스 계정이 필요 없다.
        raise HTTPException(status_code=400, detail="사장님은 관리자 화면을 이용해 주세요.")

    existing = session.exec(
        select(StaffAccount).where(StaffAccount.staff_id == payload.staff_id)
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="이미 가입 신청했거나 가입된 직원입니다.")

    account = StaffAccount(
        store_id=DEFAULT_STORE_ID,
        staff_id=staff.id,
        pin_hash=pin_service.hash_pin(payload.pin),
        status="pending",
    )
    session.add(account)
    session.commit()
    return SignupResult(
        status="pending", message="가입 신청 완료! 사장님 승인 후 로그인할 수 있어요."
    )


@router.get("/login-list", response_model=list[LoginableStaffOut])
def login_list(session: Session = Depends(get_session)) -> list[LoginableStaffOut]:
    rows = session.exec(
        select(Staff, StaffAccount)
        .join(StaffAccount, StaffAccount.staff_id == Staff.id)
        .where(
            StaffAccount.store_id == DEFAULT_STORE_ID,
            StaffAccount.status == "approved",
            Staff.is_active == True,  # noqa: E712
        )
        .order_by(Staff.name)
    ).all()
    return [LoginableStaffOut(id=s.id, name=s.name) for s, _ in rows]


@router.post("/login", response_model=LoginResult)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> LoginResult:
    staff = session.get(Staff, payload.staff_id)
    account = (
        session.exec(
            select(StaffAccount).where(StaffAccount.staff_id == payload.staff_id)
        ).first()
        if staff is not None
        else None
    )
    if (
        staff is None
        or not staff.is_active
        or account is None
        or account.status != "approved"
        or not pin_service.verify_pin(payload.pin, account.pin_hash)
    ):
        raise HTTPException(status_code=401, detail="이름 또는 PIN이 올바르지 않습니다.")

    token = staff_tokens.issue_token(staff.id)
    return LoginResult(
        token=token,
        must_change_pin=account.must_change_pin,
        staff=MeOut(
            id=staff.id,
            name=staff.name,
            role=staff.role,
            position=staff.position,
            employment_type=staff.employment_type,
            must_change_pin=account.must_change_pin,
        ),
    )
