"""연차/사전휴무 신청에서 공통으로 쓰는 기간 겹침·월별 집계 계산.

routes_leave.py / routes_dayoff.py(사장님용) 와 routes_me.py(직원 셀프서비스) 가
같은 규칙(겹치면 거부, 월 한도)을 쓰므로 여기 한 곳에 모아둔다.
"""

from datetime import date

from app.models.base import date_range


def overlaps(a1: date, a2: date, b1: date, b2: date) -> bool:
    return a1 <= b2 and b1 <= a2


def days_by_month(start: date, end: date) -> dict[tuple[int, int], int]:
    """기간이 걸친 각 달(연,월)마다 며칠씩인지."""
    out: dict[tuple[int, int], int] = {}
    for d in date_range(start, end):
        key = (d.year, d.month)
        out[key] = out.get(key, 0) + 1
    return out
