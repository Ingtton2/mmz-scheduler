"""셀프 신청 마감: 매달 20일 17시(한국시간)까지."""

from datetime import date, time

import pytest

from app.services.request_window import check_window, window_open


def test_open_before_cutoff_day():
    assert window_open(date(2026, 9, 19), time(23, 59))


def test_cutoff_day_open_until_17():
    assert window_open(date(2026, 9, 20), time(0, 0))
    assert window_open(date(2026, 9, 20), time(16, 59))


def test_cutoff_day_closed_from_17():
    assert not window_open(date(2026, 9, 20), time(17, 0))
    assert not window_open(date(2026, 9, 20), time(23, 59))


def test_closed_after_cutoff_day():
    assert not window_open(date(2026, 9, 21), time(0, 0))


def test_date_only_call_treats_cutoff_day_as_open():
    assert window_open(date(2026, 9, 20))


def test_check_window_message_mentions_cutoff():
    with pytest.raises(ValueError, match="20일 17시"):
        check_window(date(2026, 10, 5), date(2026, 10, 5), date(2026, 9, 20), time(17, 0))


def test_check_window_still_requires_next_month():
    check_window(date(2026, 10, 5), date(2026, 10, 5), date(2026, 9, 20), time(16, 59))
    with pytest.raises(ValueError, match="10월"):
        check_window(date(2026, 11, 5), date(2026, 11, 5), date(2026, 9, 20), time(16, 59))
