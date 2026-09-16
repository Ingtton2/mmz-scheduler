"""
연차 자동 계산 (스펙 3).

  잔여연차 = 부여연차(granted, 누적) - 사용연차(used, 누적)

기본휴무(base_off_days)는 연차와 별개 항목이라 계산에 넣지 않는다.
"""


def remaining(granted: float, used: float) -> float:
    """잔여연차 = 부여연차 - 사용연차."""
    return round(granted - used, 2)
