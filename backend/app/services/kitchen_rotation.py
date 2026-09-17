"""
주방 오픈/미들/마감 3인 월별 로테이션 계산 (순수 함수, DB 접근 없음).

규칙: 각자 전월 담당 기준으로 오픈→미들→마감→오픈 순서로 한 단계씩 이동.
전월 기록이 없는 사람(신규 로테이션 대상 등)은 아직 안 쓰인 슬롯을 순서대로 받는다.
"""

CYCLE = ("open", "mid", "close")


def next_slot(prev: str) -> str:
    return CYCLE[(CYCLE.index(prev) + 1) % 3]


def compute_default_rotation(
    rotation_staff_ids: list[int], prev_position_by_staff: dict[int, str]
) -> dict[int, str]:
    """이번 달 기본 로테이션 = 전월 담당을 한 칸씩 이동. 전월 기록이 없는 사람은
    아직 아무도 안 받은 슬롯을 `rotation_staff_ids` 순서대로 채운다."""
    result: dict[int, str] = {}
    used: set[str] = set()
    unresolved: list[int] = []
    for sid in rotation_staff_ids:
        prev = prev_position_by_staff.get(sid)
        if prev in CYCLE:
            nxt = next_slot(prev)
            result[sid] = nxt
            used.add(nxt)
        else:
            unresolved.append(sid)

    leftover = [p for p in CYCLE if p not in used]
    for sid, pos in zip(unresolved, leftover):
        result[sid] = pos
    return result
