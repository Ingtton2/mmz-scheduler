"""직원 셀프서비스 계정(가입/승인/로그인) API 데이터 형태 (스펙 9)."""

from datetime import datetime

from pydantic import BaseModel, field_validator

from app.schemas.leave import LeaveBalanceRead
from app.services.pin import is_valid_pin_format


def _check_pin(v: str) -> str:
    if not is_valid_pin_format(v):
        raise ValueError("PIN은 숫자 4자리여야 합니다.")
    return v


class AvailableStaffOut(BaseModel):
    """가입 신청 화면 드롭다운: 아직 계정이 없는 직원."""

    id: int
    name: str
    position: str
    role: str


class LoginableStaffOut(BaseModel):
    """로그인 화면 드롭다운: 승인된(로그인 가능한) 직원."""

    id: int
    name: str


class SignupRequest(BaseModel):
    staff_id: int
    pin: str

    @field_validator("pin")
    @classmethod
    def _v(cls, v: str) -> str:
        return _check_pin(v)


class SignupResult(BaseModel):
    status: str  # "approved" | "pending"
    message: str


class LoginRequest(BaseModel):
    staff_id: int
    pin: str


class MeOut(BaseModel):
    id: int
    name: str
    role: str
    position: str
    employment_type: str | None
    must_change_pin: bool = False
    leave: LeaveBalanceRead | None = None  # 정직원·점장만 값이 있음


class LoginResult(BaseModel):
    token: str
    must_change_pin: bool
    staff: MeOut


class ChangePinRequest(BaseModel):
    current_pin: str
    new_pin: str

    @field_validator("new_pin")
    @classmethod
    def _v(cls, v: str) -> str:
        return _check_pin(v)


class PendingAccountOut(BaseModel):
    """관리자용: 승인 대기 목록 1건."""

    account_id: int
    staff_id: int
    staff_name: str
    position: str
    role: str
    created_at: datetime


class AccountOut(BaseModel):
    """관리자용: 계정 전체 목록 1건 (승인/대기 모두)."""

    account_id: int
    staff_id: int
    staff_name: str
    status: str
    must_change_pin: bool
    created_at: datetime
    approved_at: datetime | None


class ResetPinResult(BaseModel):
    temp_pin: str  # 이 값을 사장님이 화면에서 보고 직원에게 알려줌 (다시 조회 불가)
