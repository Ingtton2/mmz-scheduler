"""
주방 오픈/미들/마감 3인 월별 로테이션 미리보기/저장 API.

  GET /api/kitchen-rotation?year=&month=  전월 기준 자동 계산값(또는 이미 저장된 값) 반환
  PUT /api/kitchen-rotation                사장님이 확인/수정한 값을 그 달 기준으로 저장

자동배치(routes_schedule.py)는 `get_or_compute_rotation()` 을 그대로 가져다 써서,
사장님이 미리 안 봤어도(=저장된 값이 없어도) 전월 기준으로 계산한 값을 자동으로
저장하고 그걸 배치 선호도로 사용한다 — 그래야 다음 달 로테이션 계산의 기준도 생긴다.
"""

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, delete, select

from app.database import get_session
from app.models import DEFAULT_STORE_ID, KitchenRotationAssignment, Staff
from app.schemas.kitchen_rotation import (
    KitchenRotationItem,
    KitchenRotationPreview,
    KitchenRotationPut,
)
from app.services.kitchen_rotation import compute_default_rotation

router = APIRouter(prefix="/kitchen-rotation", tags=["kitchen-rotation"])


def _prev_ym(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _rotation_staff(session: Session) -> list[Staff]:
    return list(
        session.exec(
            select(Staff)
            .where(
                Staff.store_id == DEFAULT_STORE_ID,
                Staff.is_active == True,  # noqa: E712
                Staff.kitchen_rotation == True,  # noqa: E712
            )
            .order_by(Staff.id)
        ).all()
    )


def _saved_rotation(session: Session, year: int, month: int) -> dict[int, str]:
    rows = session.exec(
        select(KitchenRotationAssignment).where(
            KitchenRotationAssignment.store_id == DEFAULT_STORE_ID,
            KitchenRotationAssignment.year == year,
            KitchenRotationAssignment.month == month,
        )
    ).all()
    return {r.staff_id: r.position for r in rows}


def get_or_compute_rotation(session: Session, year: int, month: int) -> dict[int, str]:
    """이 달 로테이션을 반환한다 — 이미 저장돼 있으면 그대로, 아니면 전월 기준으로
    계산해서 저장까지 하고 반환한다 (자동배치가 그대로 선호도로 쓸 수 있도록)."""
    staff = _rotation_staff(session)
    if not staff:
        return {}

    saved = _saved_rotation(session, year, month)
    if all(s.id in saved for s in staff):
        return saved

    py, pm = _prev_ym(year, month)
    prev = _saved_rotation(session, py, pm)
    computed = compute_default_rotation([s.id for s in staff], prev)

    session.exec(
        delete(KitchenRotationAssignment).where(
            KitchenRotationAssignment.store_id == DEFAULT_STORE_ID,
            KitchenRotationAssignment.year == year,
            KitchenRotationAssignment.month == month,
        )
    )
    for sid, pos in computed.items():
        session.add(
            KitchenRotationAssignment(
                store_id=DEFAULT_STORE_ID, year=year, month=month, staff_id=sid, position=pos
            )
        )
    session.commit()
    return computed


@router.get("", response_model=KitchenRotationPreview)
def preview_rotation(
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
    session: Session = Depends(get_session),
) -> KitchenRotationPreview:
    staff = _rotation_staff(session)
    saved = _saved_rotation(session, year, month)
    is_saved = bool(staff) and all(s.id in saved for s in staff)

    if is_saved:
        positions = saved
    else:
        py, pm = _prev_ym(year, month)
        prev = _saved_rotation(session, py, pm)
        positions = compute_default_rotation([s.id for s in staff], prev)

    return KitchenRotationPreview(
        year=year,
        month=month,
        items=[
            KitchenRotationItem(staff_id=s.id, staff_name=s.name, position=positions[s.id])
            for s in staff
        ],
        saved=is_saved,
    )


@router.put("", response_model=KitchenRotationPreview)
def save_rotation(
    payload: KitchenRotationPut, session: Session = Depends(get_session)
) -> KitchenRotationPreview:
    session.exec(
        delete(KitchenRotationAssignment).where(
            KitchenRotationAssignment.store_id == DEFAULT_STORE_ID,
            KitchenRotationAssignment.year == payload.year,
            KitchenRotationAssignment.month == payload.month,
        )
    )
    for item in payload.items:
        session.add(
            KitchenRotationAssignment(
                store_id=DEFAULT_STORE_ID,
                year=payload.year,
                month=payload.month,
                staff_id=item.staff_id,
                position=item.position,
            )
        )
    session.commit()
    return preview_rotation(year=payload.year, month=payload.month, session=session)
