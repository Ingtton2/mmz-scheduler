"""
연차 자동 계산 (스펙 3).

  합연차   = 전월잔여연차 + 전월발생연차
  잔여연차 = 합연차 - 연차사용

기본휴무(base_off_days)는 연차와 별개 항목이라 계산에 넣지 않는다.
"""


def total_accrued(prev_remaining: float, prev_accrued: float) -> float:
    """합연차 = 전월잔여 + 전월발생."""
    return round(prev_remaining + prev_accrued, 2)


def remaining(prev_remaining: float, prev_accrued: float, used: float) -> float:
    """잔여연차 = 합연차 - 사용."""
    return round(total_accrued(prev_remaining, prev_accrued) - used, 2)
