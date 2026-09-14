"""
직원 조회 전용 API (스펙 6.2, 7) — 로그인 없음.

QR 을 스캔하면 프론트가 /schedule/{공유코드} 로 들어오고, 그 화면이
이 API 로 스케줄 데이터를 받아 표(이미지 형태)로 보여준다.
스케줄이 "임시(draft)" 상태면 — 공유 전이거나, 공유 후 다시 수정된 경우 —
사장님이 다시 "공유"를 누르기 전까지는 여기서 막힌다.

  GET /api/public/schedule/{share_code}  -> 공유된 스케줄 (없거나 아직 임시면 404)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Schedule
from app.schemas.schedule import PublicScheduleResult
from app.services.schedule_view import build_public_view

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/schedule/{share_code}", response_model=PublicScheduleResult)
def public_schedule(
    share_code: str, session: Session = Depends(get_session)
) -> PublicScheduleResult:
    sched = session.exec(
        select(Schedule).where(Schedule.share_code == share_code)
    ).first()
    if sched is None:
        raise HTTPException(status_code=404, detail="스케줄을 찾을 수 없습니다.")
    if sched.status != "confirmed":
        raise HTTPException(status_code=404, detail="아직 스케줄이 공유되지 않았습니다.")

    return build_public_view(session, sched)
