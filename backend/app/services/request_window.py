"""
직원 셀프서비스 연차/사전휴무 신청 가능 기간 (스펙 9-5).

규칙: "다음 달" 스케줄에 대해서만, 이번 달 20일까지만 셀프 신청 가능.
  예) 오늘이 9월이면 -> 10월 신청만 가능, 9월 20일까지만.
  20일이 지나면 셀프 신청은 막고, 이후엔 사장님이 관리자 화면에서 직접 등록한다
  (관리자 화면 쪽 API는 이 제한을 받지 않음 — routes_leave.py/routes_dayoff.py 그대로).
"""

from datetime import date

CUTOFF_DAY = 20


def allowed_target_month(today: date) -> tuple[int, int]:
    """오늘 기준 셀프 신청 대상이 되는 '다음 달' (year, month)."""
    if today.month == 12:
        return today.year + 1, 1
    return today.year, today.month + 1


def window_open(today: date) -> bool:
    return today.day <= CUTOFF_DAY


def check_window(start: date, end: date, today: date) -> None:
    """신청 기간이 셀프 신청 허용 범위 밖이면 ValueError."""
    if not window_open(today):
        raise ValueError(
            f"이번 달 {CUTOFF_DAY}일이 지나 셀프 신청 기간이 아닙니다. "
            "사장님께 말씀해서 관리자 화면에서 등록해 주세요."
        )
    y, m = allowed_target_month(today)
    if (start.year, start.month) != (y, m) or (end.year, end.month) != (y, m):
        raise ValueError(f"지금은 {y}년 {m}월 스케줄만 신청할 수 있습니다.")
