"""
공휴일(대체공휴일 포함) 등록 API — 관리자가 날짜를 직접 등록/삭제한다.

  GET    /api/holidays        등록된 공휴일 전체 (날짜순)
  POST   /api/holidays        공휴일 등록 (이미 있는 날짜면 이름만 갱신)
  DELETE /api/holidays/{id}   공휴일 삭제
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import DEFAULT_STORE_ID, Holiday
from app.schemas.holiday import HolidayCreate, HolidayItem

router = APIRouter(prefix="/holidays", tags=["holidays"])


def _to_item(row: Holiday) -> HolidayItem:
    return HolidayItem(id=row.id, date=row.date, name=row.name)


@router.get("", response_model=list[HolidayItem])
def list_holidays(session: Session = Depends(get_session)) -> list[HolidayItem]:
    rows = session.exec(
        select(Holiday)
        .where(Holiday.store_id == DEFAULT_STORE_ID)
        .order_by(Holiday.date)
    ).all()
    return [_to_item(r) for r in rows]


@router.post("", response_model=HolidayItem)
def create_holiday(
    payload: HolidayCreate, session: Session = Depends(get_session)
) -> HolidayItem:
    existing = session.exec(
        select(Holiday).where(
            Holiday.store_id == DEFAULT_STORE_ID, Holiday.date == payload.date
        )
    ).first()
    if existing:
        existing.name = payload.name
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return _to_item(existing)

    row = Holiday(store_id=DEFAULT_STORE_ID, date=payload.date, name=payload.name)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_item(row)


@router.delete("/{holiday_id}", status_code=204)
def delete_holiday(holiday_id: int, session: Session = Depends(get_session)) -> None:
    row = session.get(Holiday, holiday_id)
    if row is None or row.store_id != DEFAULT_STORE_ID:
        raise HTTPException(status_code=404, detail="공휴일을 찾을 수 없습니다.")
    session.delete(row)
    session.commit()
