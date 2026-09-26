"""
"휴가 일정 공유" 메모판에서 보여주는 달 범위.

시작은 "이번 달"(한국시간)이라 달이 지나면 자동으로 앞이 줄어든다.
단 WINDOW_START(2026년 11월) 전에는 그 달부터 보여준다.
끝은 WINDOW_END(현재 2027년 12월)까지 — 늘리려면 이 값만 바꾸면 된다.
그 날짜가 가까워져 남은 달이 너무 적어지면 최소 MIN_MONTHS 개월은 보여준다
(해가 바뀌어도 화면이 비지 않도록).
"""

from datetime import date

WINDOW_START = (2026, 11)
WINDOW_END = (2027, 12)
MIN_MONTHS = 12


def month_key(y: int, m: int) -> str:
    return f"{y}-{m:02d}"


def _add_months(y: int, m: int, n: int) -> tuple[int, int]:
    total = y * 12 + (m - 1) + n
    return total // 12, total % 12 + 1


def window_months(today: date) -> list[str]:
    """이번 달(또는 WINDOW_START)부터 WINDOW_END 까지의 "YYYY-MM" 목록 (최소 MIN_MONTHS 개)."""
    start = max(WINDOW_START, (today.year, today.month))
    end = max(WINDOW_END, _add_months(*start, MIN_MONTHS - 1))
    out: list[str] = []
    y, m = start
    while (y, m) <= end:
        out.append(month_key(y, m))
        y, m = _add_months(y, m, 1)
    return out
