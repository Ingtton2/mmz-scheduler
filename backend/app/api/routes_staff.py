"""
직원 등록/조회/수정/삭제 + 연차 정보 API (스펙 6.1, 3).

  GET    /api/staff              직원 목록 (재직 중, 연차 정보 포함)
  POST   /api/staff              직원 등록
  PATCH  /api/staff/{id}         직원 기본정보 수정 (이름/포지션/역할/고용형태/근무요일)
  DELETE /api/staff/{id}         직원 삭제 (is_active=False, 기록은 남김)
  PATCH  /api/staff/{id}/leave   직원 연차 숫자 수정 (정직원만) -> 잔여연차 자동 재계산
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import DEFAULT_STORE_ID, LeaveBalance, Staff
from app.schemas.leave import LeaveBalanceInput, LeaveBalanceRead
from app.schemas.staff import StaffCreate, StaffRead, StaffUpdate, has_leave_balance

router = APIRouter(prefix="/staff", tags=["staff"])


def _wd_to_list(csv: str) -> list[int]:
    return sorted({int(x) for x in csv.split(",") if x.strip() != ""})


def _wd_to_csv(days: list[int]) -> str:
    return ",".join(str(d) for d in sorted(set(days)))


def _get_balance(session: Session, staff_id: int) -> LeaveBalance | None:
    return session.exec(
        select(LeaveBalance).where(LeaveBalance.staff_id == staff_id)
    ).first()


def _to_read(staff: Staff, bal: LeaveBalance | None) -> StaffRead:
    leave = None
    if has_leave_balance(staff.role, staff.employment_type) and bal is not None:
        leave = LeaveBalanceRead.from_values(
            base_off_days=bal.base_off_days,
            granted=bal.granted,
            used=bal.used,
        )
    return StaffRead(
        id=staff.id,
        store_id=staff.store_id,
        name=staff.name,
        employment_type=staff.employment_type,
        position=staff.position,
        role=staff.role,
        work_weekdays=_wd_to_list(staff.work_weekdays),
        fixed_schedule=staff.fixed_schedule,
        is_active=staff.is_active,
        hire_date=staff.hire_date,
        created_at=staff.created_at,
        leave=leave,
    )


def _staff_or_404(session: Session, staff_id: int) -> Staff:
    staff = session.get(Staff, staff_id)
    if staff is None or staff.store_id != DEFAULT_STORE_ID:
        raise HTTPException(status_code=404, detail="해당 직원을 찾을 수 없습니다.")
    return staff


@router.get("", response_model=list[StaffRead])
def list_staff(session: Session = Depends(get_session)) -> list[StaffRead]:
    staff_rows = session.exec(
        select(Staff)
        .where(Staff.store_id == DEFAULT_STORE_ID, Staff.is_active == True)  # noqa: E712
        .order_by(Staff.created_at)
    ).all()
    return [_to_read(s, _get_balance(session, s.id)) for s in staff_rows]


@router.post("", response_model=StaffRead, status_code=201)
def create_staff(payload: StaffCreate, session: Session = Depends(get_session)) -> StaffRead:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="이름을 입력해 주세요.")

    staff = Staff(
        store_id=DEFAULT_STORE_ID,
        name=name,
        employment_type=payload.employment_type.value if payload.employment_type else None,
        position=payload.position.value,
        role=payload.role.value,
        work_weekdays=_wd_to_csv(payload.work_weekdays),
        fixed_schedule=payload.fixed_schedule,
        hire_date=payload.hire_date,
    )
    session.add(staff)
    session.commit()
    session.refresh(staff)

    bal = None
    if has_leave_balance(staff.role, staff.employment_type):
        bal = LeaveBalance(
            store_id=DEFAULT_STORE_ID,
            staff_id=staff.id,
            base_off_days=payload.leave.base_off_days,
            granted=payload.leave.granted,
            used=payload.leave.used,
        )
        session.add(bal)
        session.commit()
        session.refresh(bal)

    return _to_read(staff, bal)


@router.patch("/{staff_id}", response_model=StaffRead)
def update_staff(
    staff_id: int, payload: StaffUpdate, session: Session = Depends(get_session)
) -> StaffRead:
    staff = _staff_or_404(session, staff_id)

    if payload.name is not None:
        n = payload.name.strip()
        if not n:
            raise HTTPException(status_code=422, detail="이름을 입력해 주세요.")
        staff.name = n
    if payload.position is not None:
        staff.position = payload.position.value
    if payload.role is not None:
        staff.role = payload.role.value
    if payload.employment_type is not None:
        staff.employment_type = payload.employment_type.value
    if payload.work_weekdays is not None:
        staff.work_weekdays = _wd_to_csv(payload.work_weekdays)
    if payload.fixed_schedule is not None:
        staff.fixed_schedule = payload.fixed_schedule
    if payload.hire_date is not None:
        staff.hire_date = payload.hire_date

    # 사장님으로 바꾸면 고용형태 없음
    if staff.role == "owner":
        staff.employment_type = None

    session.add(staff)
    session.commit()
    session.refresh(staff)

    bal = _get_balance(session, staff_id)
    # 정직원이 아니게 되면 남아있는 연차 잔액 행은 무시됨(_to_read 에서 걸러짐).
    # 정직원이 되었는데 잔액 행이 없으면 0으로 만들어 준다.
    if has_leave_balance(staff.role, staff.employment_type) and bal is None:
        bal = LeaveBalance(store_id=DEFAULT_STORE_ID, staff_id=staff_id)
        session.add(bal)
        session.commit()
        session.refresh(bal)

    return _to_read(staff, bal)


@router.patch("/{staff_id}/leave", response_model=StaffRead)
def update_leave(
    staff_id: int, payload: LeaveBalanceInput, session: Session = Depends(get_session)
) -> StaffRead:
    staff = _staff_or_404(session, staff_id)
    if not has_leave_balance(staff.role, staff.employment_type):
        raise HTTPException(
            status_code=400, detail="연차 정보는 정직원만 관리합니다."
        )

    bal = _get_balance(session, staff_id)
    if bal is None:
        bal = LeaveBalance(store_id=DEFAULT_STORE_ID, staff_id=staff_id)
    bal.base_off_days = payload.base_off_days
    bal.granted = payload.granted
    bal.used = payload.used
    session.add(bal)
    session.commit()
    session.refresh(bal)

    return _to_read(staff, bal)


@router.delete("/{staff_id}", status_code=204)
def delete_staff(staff_id: int, session: Session = Depends(get_session)) -> None:
    staff = _staff_or_404(session, staff_id)
    staff.is_active = False
    session.add(staff)
    session.commit()
