"""저장된 스케줄 셀(dict[date_str, work_code])에서 요약(ShiftSummary)을 계산.

routes_schedule.py(사장님 화면)와 routes_me.py(직원 "내 스케줄")가 공유한다.
"""

from app.schemas.schedule import ShiftSummary

# 코드 -> (슬롯 키, 포지션 키 or None)
CODE_TO_KEY: dict[str, tuple[str, str | None]] = {
    "FO": ("open", "hall"),
    "FC": ("close", "hall"),
    "BO": ("open", "kitchen"),
    "BM": ("mid", "kitchen"),
    "BC": ("close", "kitchen"),
    "풀오마": ("full", None),
    "D/O": ("off", None),
    "연차": ("leave", None),
    "사휴": ("blocked", None),
    # 구버전 저장분 호환
    "O": ("open", None),
    "M": ("mid", None),
    "C": ("close", None),
}


def summarize(cells: dict[str, str]) -> ShiftSummary:
    acc = {
        k: 0
        for k in ("open", "mid", "close", "full", "hall", "kitchen", "off", "leave", "blocked")
    }
    for code in cells.values():
        info = CODE_TO_KEY.get(code)
        if not info:
            continue
        acc[info[0]] += 1
        if info[1]:
            acc[info[1]] += 1
    return ShiftSummary(
        work=acc["open"] + acc["mid"] + acc["close"] + acc["full"], **acc
    )
