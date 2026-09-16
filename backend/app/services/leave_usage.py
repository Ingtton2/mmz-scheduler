"""
연차 신청(LeaveRequest) 승인/취소 시 사용연차(LeaveBalance.used) 반영 + 사용 이력 기록.

사전 휴무 신청은 연차를 차감하지 않으므로 이 로직은 연차 전용이다.
"""

from datetime import date

from sqlmodel import Session, select

from app.models import LeaveBalance, LeaveRequest, LeaveUsageLog, Staff
from app.schemas.staff import has_leave_balance


def _days(start: date, end: date) -> int:
    return (end - start).days + 1


def _get_or_create_balance(session: Session, store_id: int, staff_id: int) -> LeaveBalance:
    bal = session.exec(select(LeaveBalance).where(LeaveBalance.staff_id == staff_id)).first()
    if bal is None:
        bal = LeaveBalance(store_id=store_id, staff_id=staff_id)
    return bal


def _usage_log(session: Session, request_id: int) -> LeaveUsageLog | None:
    return session.exec(
        select(LeaveUsageLog).where(LeaveUsageLog.leave_request_id == request_id)
    ).first()


def sync_on_status_change(
    session: Session, req: LeaveRequest, old_status: str, old_start: date, old_end: date
) -> None:
    """req 는 (커밋 전) 변경이 반영된 상태. old_* 는 변경 전 값.
    "승인 안 됨 -> 승인" / "승인 -> 승인 아님" / "승인 상태에서 날짜만 수정" 세 경우를 처리한다."""
    staff = session.get(Staff, req.staff_id)
    if staff is None or not has_leave_balance(staff.role, staff.employment_type):
        return  # 연차 대상이 아니면 무시 (파트타임/사장님에게 실수로 등록된 경우 등)

    was_confirmed = old_status == "confirmed"
    is_confirmed = req.status == "confirmed"
    existing_log = _usage_log(session, req.id) if req.id is not None else None

    if not was_confirmed and is_confirmed:
        bal = _get_or_create_balance(session, req.store_id, req.staff_id)
        days = _days(req.start_date, req.end_date)
        bal.used += days
        session.add(bal)
        session.add(
            LeaveUsageLog(
                store_id=req.store_id,
                staff_id=req.staff_id,
                leave_request_id=req.id,
                start_date=req.start_date,
                end_date=req.end_date,
                days=days,
                applied_at=req.applied_at,
                remaining_after=bal.granted - bal.used,
            )
        )
    elif was_confirmed and not is_confirmed:
        bal = _get_or_create_balance(session, req.store_id, req.staff_id)
        bal.used -= _days(old_start, old_end)
        session.add(bal)
        if existing_log is not None:
            session.delete(existing_log)
    elif was_confirmed and is_confirmed:
        old_days = _days(old_start, old_end)
        new_days = _days(req.start_date, req.end_date)
        if old_days != new_days or existing_log is None:
            bal = _get_or_create_balance(session, req.store_id, req.staff_id)
            bal.used += new_days - old_days
            session.add(bal)
            if existing_log is not None:
                existing_log.start_date = req.start_date
                existing_log.end_date = req.end_date
                existing_log.days = new_days
                existing_log.applied_at = req.applied_at
                existing_log.remaining_after = bal.granted - bal.used
                session.add(existing_log)


def reverse_on_delete(session: Session, req: LeaveRequest) -> None:
    """연차 신청 자체를 삭제할 때 — 승인된 상태였다면 사용량/이력을 되돌린다."""
    if req.status != "confirmed":
        return
    staff = session.get(Staff, req.staff_id)
    if staff is None or not has_leave_balance(staff.role, staff.employment_type):
        return
    bal = _get_or_create_balance(session, req.store_id, req.staff_id)
    bal.used -= _days(req.start_date, req.end_date)
    session.add(bal)
    existing_log = _usage_log(session, req.id)
    if existing_log is not None:
        session.delete(existing_log)
