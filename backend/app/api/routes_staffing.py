"""
요일/시간대별 필요 인원 설정 API (스펙 4).

  GET  /api/staffing-requirements   현재 설정 전체 (7요일 x 2포지션)
  PUT  /api/staffing-requirements   설정 전체 교체 (화면이 통째로 보냄)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, delete, select

from app.database import get_session
from app.models import DEFAULT_STORE_ID, StaffingRequirement, Store
from app.schemas.staffing import (
    DailyHeadcountTarget,
    StaffingRequirementItem,
    StaffingRequirementsPut,
)

router = APIRouter(prefix="/staffing-requirements", tags=["staffing"])


def _to_item(row: StaffingRequirement) -> StaffingRequirementItem:
    return StaffingRequirementItem(
        weekday=row.weekday,
        position=row.position,
        time_slot=row.time_slot,
        min_headcount=row.min_headcount,
    )


@router.get("", response_model=list[StaffingRequirementItem])
def get_requirements(
    session: Session = Depends(get_session),
) -> list[StaffingRequirementItem]:
    rows = session.exec(
        select(StaffingRequirement)
        .where(StaffingRequirement.store_id == DEFAULT_STORE_ID)
        .order_by(
            StaffingRequirement.weekday,
            StaffingRequirement.position,
            StaffingRequirement.time_slot,
        )
    ).all()
    return [_to_item(r) for r in rows]


@router.put("", response_model=list[StaffingRequirementItem])
def put_requirements(
    payload: StaffingRequirementsPut, session: Session = Depends(get_session)
) -> list[StaffingRequirementItem]:
    session.exec(
        delete(StaffingRequirement).where(
            StaffingRequirement.store_id == DEFAULT_STORE_ID
        )
    )

    # (weekday, position, time_slot) 중복은 마지막 값으로 정리
    dedup: dict[tuple[int, str, str], StaffingRequirementItem] = {}
    for item in payload.items:
        dedup[(item.weekday, item.position, item.time_slot)] = item

    for item in dedup.values():
        session.add(
            StaffingRequirement(
                store_id=DEFAULT_STORE_ID,
                weekday=item.weekday,
                time_slot=item.time_slot,
                position=item.position,
                min_headcount=item.min_headcount,
            )
        )
    session.commit()
    return get_requirements(session)


@router.get("/daily-headcount-target", response_model=DailyHeadcountTarget)
def get_daily_headcount_target(
    session: Session = Depends(get_session),
) -> DailyHeadcountTarget:
    store = session.get(Store, DEFAULT_STORE_ID)
    if store is None:
        raise HTTPException(status_code=404, detail="매장 정보가 없습니다.")
    return DailyHeadcountTarget(daily_headcount_target=store.daily_headcount_target)


@router.put("/daily-headcount-target", response_model=DailyHeadcountTarget)
def put_daily_headcount_target(
    payload: DailyHeadcountTarget, session: Session = Depends(get_session)
) -> DailyHeadcountTarget:
    store = session.get(Store, DEFAULT_STORE_ID)
    if store is None:
        raise HTTPException(status_code=404, detail="매장 정보가 없습니다.")
    store.daily_headcount_target = payload.daily_headcount_target
    session.add(store)
    session.commit()
    return DailyHeadcountTarget(daily_headcount_target=store.daily_headcount_target)
