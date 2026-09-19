"""모델 공통 조각."""

from datetime import date, datetime, timedelta, timezone


# 한국은 서머타임이 없어서 고정 +9시간으로 충분하다. 서버(Render)는 UTC 라서
# "오늘 날짜"·마감 시각처럼 사람이 보는 날짜는 항상 이 시간대 기준으로 만든다.
KST = timezone(timedelta(hours=9))


def kst_now() -> datetime:
    """현재 시각(한국시간, tz-aware)."""
    return datetime.now(KST)


def today_kst() -> date:
    """오늘 날짜(한국시간). 신청일·부여일 기본값 등에 사용."""
    return kst_now().date()


def utcnow() -> datetime:
    """현재 시각(UTC). created_at 등의 기본값으로 사용."""
    return datetime.now(timezone.utc)


def date_range(start: date, end: date) -> list[date]:
    """start ~ end (양끝 포함) 사이의 모든 날짜."""
    if end < start:
        return []
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]
