"""저장된 스케줄 셀에서 필요인원 부족/초과 경고를 다시 계산한다.

자동배치 직후에는 엔진이 경고를 만들어 주지만, 저장된 근무표를 다시 열거나 표의 칸을
직접 고친 뒤에는 엔진이 안 돌기 때문에 여기서 같은 기준(포지션 x 시간대 필요인원,
하루 총원 상한 = max(필요인원 합, 하루 총 출근 인원 목표))으로 다시 센다.
"""

from datetime import date

from app.schemas.schedule import ScheduleWarningOut

_POS_LABEL = {"hall": "홀", "kitchen": "주방"}
_SLOT_LABEL = {"open": "오픈", "mid": "미들", "close": "마감"}
_SLOTS = ("open", "mid", "close")

# 근무 코드 -> (포지션, 슬롯)
_CODE_SLOT = {
    "FO": ("hall", "open"),
    "FC": ("hall", "close"),
    "BO": ("kitchen", "open"),
    "BM": ("kitchen", "mid"),
    "BC": ("kitchen", "close"),
}
_WORK_CODES = set(_CODE_SLOT) | {"풀오마"}


def check_headcount(
    days: list[str],
    cells_by_staff: dict[int, dict[str, str]],
    part_time_position: dict[int, str],
    requirements: dict[int, dict[str, dict[str, int]]],
    daily_headcount_target: int = 0,
) -> list[ScheduleWarningOut]:
    """part_time_position: 파트타임 직원 id -> 포지션(hall/kitchen/both). 풀오마는 그 포지션
    모든 슬롯을 커버하는 것으로 센다 (both 는 홀로 취급)."""
    if not any(
        c in _WORK_CODES for cells in cells_by_staff.values() for c in cells.values()
    ):
        return []  # 아직 배치가 없는 스케줄(빈 칸)에는 경고를 만들지 않는다

    out: list[ScheduleWarningOut] = []
    for day in days:
        wd = date.fromisoformat(day).weekday()
        counts = {(p, s): 0 for p in _POS_LABEL for s in _SLOTS}
        total = 0
        for sid, cells in cells_by_staff.items():
            code = cells.get(day)
            if code not in _WORK_CODES:
                continue
            total += 1
            if code == "풀오마":
                pos = "kitchen" if part_time_position.get(sid) == "kitchen" else "hall"
                for slot in _SLOTS:
                    if pos == "hall" and slot == "mid":
                        continue  # 홀은 미들 없음
                    counts[(pos, slot)] += 1
            else:
                counts[_CODE_SLOT[code]] += 1

        day_req_sum = 0
        for pos in _POS_LABEL:
            for slot in _SLOTS:
                req = int(requirements.get(wd, {}).get(pos, {}).get(slot, 0))
                day_req_sum += req
                got = counts[(pos, slot)]
                if got < req:
                    out.append(
                        ScheduleWarningOut(
                            date=day,
                            position=f"{_POS_LABEL[pos]}·{_SLOT_LABEL[slot]}",
                            needed=req,
                            filled=got,
                            message=f"{day} {_POS_LABEL[pos]} {_SLOT_LABEL[slot]}: "
                            f"{req}명 필요, {got}명 (−{req - got})",
                        )
                    )

        cap = max(day_req_sum, daily_headcount_target)
        if cap > 0 and total > cap:
            out.append(
                ScheduleWarningOut(
                    date=day,
                    position="총원",
                    needed=cap,
                    filled=total,
                    message=f"{day}: 필요인원 {cap}명인데 {total}명 배치 (+{total - cap})",
                )
            )
    return out
