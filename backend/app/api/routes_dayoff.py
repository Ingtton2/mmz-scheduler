"""
사전 휴무 신청 API (스펙 3.1) — 기간(시작일~종료일) 단위.

연차와 별개. 직원 1명당 한 달 최대 20일. 자동배치에선 그 날짜 배치 금지(하드)로
쓰지만 근무일수는 줄이지 않는다 (다른 날로 옮겨 채움).

  GET    /api/dayoff-requests        신청 목록 (직원 이름 포함, 시작일순)
  POST   /api/dayoff-requests        신청 추가 (기간 겹침 / 월 한도 초과 거부)
  PATCH  /api/dayoff-requests/{id}   상태 변경(대기<->승인<->반려) 등 수정
  DELETE /api/dayoff-requests/{id}   신청 삭제
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import MAX_PER_MONTH, DEFAULT_STORE_ID, DayOffRequest, Staff
from app.models.base import today_kst
from app.schemas.dayoff import DayOffRequestCreate, DayOffRequestRead, DayOffRequestUpdate
from app.services.date_overlap import days_by_month, overlaps as _overlaps

router = APIRouter(prefix="/dayoff-requests", tags=["dayoff-requests"])


def _days(start: date, end: date) -> int:
    return (end - start).days + 1


def _to_read(req: DayOffRequest, staff_name: str) -> DayOffRequestRead:
    return DayOffRequestRead(
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


@router.get("", response_model=list[DayOffRequestRead])
def list_requests(session: Session = Depends(get_session)) -> list[DayOffRequestRead]:
    rows = session.exec(
        select(DayOffRequest, Staff)
        .join(Staff, Staff.id == DayOffRequest.staff_id)
        .where(DayOffRequest.store_id == DEFAULT_STORE_ID)
        .order_by(DayOffRequest.start_date)
    ).all()
    return [_to_read(req, staff.name) for req, staff in rows]


@router.post("", response_model=DayOffRequestRead, status_code=201)
def create_request(
    payload: DayOffRequestCreate, session: Session = Depends(get_session)
) -> DayOffRequestRead:
    staff = session.get(Staff, payload.staff_id)
    if staff is None or staff.store_id != DEFAULT_STORE_ID:
        raise HTTPException(status_code=404, detail="해당 직원을 찾을 수 없습니다.")

    existing = session.exec(
        select(DayOffRequest).where(
            DayOffRequest.store_id == DEFAULT_STORE_ID,
            DayOffRequest.staff_id == payload.staff_id,
        )
    ).all()

    if any(
        _overlaps(payload.start_date, payload.end_date, r.start_date, r.end_date)
        for r in existing
    ):
        raise HTTPException(status_code=409, detail="이미 신청한 기간과 겹칩니다.")

    # 월별 한도: 새 기간이 걸친 각 달마다 (기존 + 새) 일수가 한도 이하여야 함
    new_by_month = days_by_month(payload.start_date, payload.end_date)

    exist_by_month: dict[tuple[int, int], int] = {}
    for r in existing:
        for ym, cnt in days_by_month(r.start_date, r.end_date).items():
            exist_by_month[ym] = exist_by_month.get(ym, 0) + cnt

    for ym, cnt in new_by_month.items():
        if exist_by_month.get(ym, 0) + cnt > MAX_PER_MONTH:
            raise HTTPException(
                status_code=422,
                detail=f"사전 휴무 신청은 한 달 최대 {MAX_PER_MONTH}일까지입니다.",
            )

    req = DayOffRequest(
        store_id=DEFAULT_STORE_ID,
        staff_id=payload.staff_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        applied_at=payload.applied_at or today_kst(),
        status=payload.status.value,
        note=(payload.note or None),
    )
    session.add(req)
    session.commit()
    session.refresh(req)
    return _to_read(req, staff.name)


@router.patch("/{request_id}", response_model=DayOffRequestRead)
def update_request(
    request_id: int, payload: DayOffRequestUpdate, session: Session = Depends(get_session)
) -> DayOffRequestRead:
    req = session.get(DayOffRequest, request_id)
    if req is None or req.store_id != DEFAULT_STORE_ID:
        raise HTTPException(status_code=404, detail="해당 신청을 찾을 수 없습니다.")

    if payload.status is not None:
        req.status = payload.status.value
    if payload.start_date is not None:
        req.start_date = payload.start_date
    if payload.end_date is not None:
        req.end_date = payload.end_date
    if payload.applied_at is not None:
        req.applied_at = payload.applied_at
    if payload.note is not None:
        req.note = payload.note or None
    if req.end_date < req.start_date:
        raise HTTPException(status_code=422, detail="종료일이 시작일보다 빠릅니다.")

    session.add(req)
    session.commit()
    session.refresh(req)

    staff = session.get(Staff, req.staff_id)
    return _to_read(req, staff.name if staff else "(삭제된 직원)")


@router.delete("/{request_id}", status_code=204)
def delete_request(request_id: int, session: Session = Depends(get_session)) -> None:
    req = session.get(DayOffRequest, request_id)
    if req is None or req.store_id != DEFAULT_STORE_ID:
        raise HTTPException(status_code=404, detail="해당 신청을 찾을 수 없습니다.")
    session.delete(req)
    session.commit()
