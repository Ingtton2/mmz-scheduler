"""모델 공통 조각."""

from datetime import date, datetime, timedelta, timezone


def utcnow() -> datetime:
    """현재 시각(UTC). created_at 등의 기본값으로 사용."""
    return datetime.now(timezone.utc)


def date_range(start: date, end: date) -> list[date]:
    """start ~ end (양끝 포함) 사이의 모든 날짜."""
    if end < start:
        return []
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]
