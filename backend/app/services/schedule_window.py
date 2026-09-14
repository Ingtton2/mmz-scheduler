"""
스케줄 자동배치/수동수정/직원조회에 대한 시점(당월 기준) 제한 규칙.

  - 자동배치(전체 재계산): 당월 포함 과거는 금지. 다음 달부터만 가능.
    (이미 지나갔거나 진행 중인 근무표를 알고리즘이 통째로 새로 짜버리면 안 됨)
  - 수동 수정(칸 단위): 과거(당월 이전)만 금지. 당월은 급한 변경 대응을 위해
    계속 허용 (직원이 갑자기 아프거나 그만두는 경우 등).
  - 직원 조회: 과거 + 당월 + "공유됨" 상태인 다음 달까지만. 그 이후(당월+2달째
    부터)는 공유 상태와 무관하게 항상 차단 — 사장님이 실수로 더 먼 미래를
    공유해도 직원에게는 안 보이는 안전장치.
"""

from datetime import date

Ym = tuple[int, int]


def _ym(year: int, month: int) -> Ym:
    return (year, month)


def current_ym(today: date) -> Ym:
    return (today.year, today.month)


def next_ym(today: date) -> Ym:
    y, m = current_ym(today)
    return (y + 1, 1) if m == 12 else (y, m + 1)


def can_run_auto_schedule(year: int, month: int, today: date) -> bool:
    """자동배치는 다음 달부터만 (당월 포함 과거는 금지)."""
    return _ym(year, month) > current_ym(today)


def can_manual_edit(year: int, month: int, today: date) -> bool:
    """수동 수정은 당월부터 계속 가능 (과거만 금지)."""
    return _ym(year, month) >= current_ym(today)


def within_employee_visible_range(year: int, month: int, today: date) -> bool:
    """직원 조회 가능 범위: 과거 + 당월 + 다음 달까지. 그 이후는 항상 차단."""
    return _ym(year, month) <= next_ym(today)
