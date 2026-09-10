"""
직원 API 가 주고받는 데이터 형태.

- StaffCreate : 화면 -> 서버 (직원 등록)
- StaffUpdate : 화면 -> 서버 (직원 기본정보 수정)
- StaffRead   : 서버 -> 화면 (저장된 직원 1명 + 연차 정보)

규칙:
  - 고용형태(employment_type): 일반 직원만 필수. 사장님이면 None.
  - 사장님의 "홀만 / 홀+주방" 구분은 포지션(hall / both) 으로 표현. (스펙 2.2)
  - 연차 정보(leave): 정직원만. 파트타임/사장님은 연차 없음 -> None.
  - 근무 가능 요일(work_weekdays): 0=월 ~ 6=일. 기본 전체. 파트타임 요일 고정용.
"""

from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator

from app.models.enums import EmploymentType, Position, StaffRole
from app.schemas.leave import LeaveBalanceInput, LeaveBalanceRead

ALL_WEEKDAYS = [0, 1, 2, 3, 4, 5, 6]


def _clean_weekdays(v: list[int]) -> list[int]:
    out = sorted({int(x) for x in v})
    if not out or any(d < 0 or d > 6 for d in out):
        raise ValueError("근무 가능 요일은 0(월)~6(일) 중에서 하나 이상 골라야 합니다.")
    return out


class StaffCreate(BaseModel):
    name: str
    position: Position
    role: StaffRole = StaffRole.STAFF
    employment_type: EmploymentType | None = None
    work_weekdays: list[int] = ALL_WEEKDAYS
    fixed_schedule: bool = False
    # 연차 숫자 (정직원만 실제로 저장됨)
    leave: LeaveBalanceInput = LeaveBalanceInput()

    @field_validator("work_weekdays")
    @classmethod
    def _check_wd(cls, v: list[int]) -> list[int]:
        return _clean_weekdays(v)

    @model_validator(mode="after")
    def check_rules(self):
        # 사장님은 고용형태 없음. 일반 직원 / 점장은 고용형태 필수.
        if self.role == StaffRole.OWNER:
            self.employment_type = None
        elif self.employment_type is None:
            raise ValueError("고용형태(정직원/파트타임)를 선택해 주세요.")
        return self


class StaffUpdate(BaseModel):
    """직원 기본정보 수정. 연차 숫자는 별도 엔드포인트(/staff/{id}/leave)."""
    name: str | None = None
    position: Position | None = None
    role: StaffRole | None = None
    employment_type: EmploymentType | None = None
    work_weekdays: list[int] | None = None
    fixed_schedule: bool | None = None

    @field_validator("work_weekdays")
    @classmethod
    def _check_wd(cls, v: list[int] | None) -> list[int] | None:
        return _clean_weekdays(v) if v is not None else v


class StaffRead(BaseModel):
    id: int
    store_id: int
    name: str
    employment_type: str | None
    position: str
    role: str
    work_weekdays: list[int]
    fixed_schedule: bool
    is_active: bool
    created_at: datetime
    leave: LeaveBalanceRead | None  # 정직원만 값이 있음

    model_config = {"from_attributes": True}


def has_leave_balance(role: str, employment_type: str | None) -> bool:
    """연차·기본휴무 관리 대상인가? 정직원 + 점장(정직원)."""
    return role in ("staff", "manager") and employment_type == "full_time"
