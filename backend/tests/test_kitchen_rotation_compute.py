"""주방 로테이션 계산 순수 함수 테스트."""

from app.services.kitchen_rotation import compute_default_rotation, next_slot


def test_next_slot_cycles_open_mid_close():
    assert next_slot("open") == "mid"
    assert next_slot("mid") == "close"
    assert next_slot("close") == "open"


def test_compute_default_rotation_shifts_each_by_one_step():
    prev = {1: "close", 2: "open", 3: "mid"}
    result = compute_default_rotation([1, 2, 3], prev)
    assert result == {1: "open", 2: "mid", 3: "close"}


def test_compute_default_rotation_bootstraps_when_no_prior_data():
    result = compute_default_rotation([7, 6, 4], {})
    assert set(result.values()) == {"open", "mid", "close"}
    assert len(result) == 3


def test_compute_default_rotation_fills_leftover_for_new_member_only():
    """기존 2명은 전월 기록대로 이동하고, 신규 1명만 남은 슬롯을 받는다."""
    prev = {1: "open", 2: "mid"}  # 3번은 이번 달 신규 로테이션 대상
    result = compute_default_rotation([1, 2, 3], prev)
    assert result[1] == "mid"
    assert result[2] == "close"
    assert result[3] == "open"  # 남은 슬롯
    assert set(result.values()) == {"open", "mid", "close"}


def test_compute_default_rotation_three_month_cycle_returns_to_start():
    start = {1: "open", 2: "mid", 3: "close"}
    m1 = compute_default_rotation([1, 2, 3], start)
    m2 = compute_default_rotation([1, 2, 3], m1)
    m3 = compute_default_rotation([1, 2, 3], m2)
    assert m3 == start
