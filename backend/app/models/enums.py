"""
앱 전체에서 쓰는 '정해진 선택지' 목록.

DB 에는 아래 값들이 그대로 문자열로 저장됩니다 (예: "full_time").
화면에 보여줄 한글 이름은 프론트엔드에서 매핑합니다
(frontend/src/labels.ts).
"""

from enum import Enum


class EmploymentType(str, Enum):
    """고용형태 (스펙 2.1)"""
    FULL_TIME = "full_time"   # 정직원
    PART_TIME = "part_time"   # 파트타임


class Position(str, Enum):
    """포지션 (스펙 2.1)"""
    HALL = "hall"       # 홀 전담
    KITCHEN = "kitchen"  # 주방 전담
    BOTH = "both"        # 겸직 (홀+주방)


class StaffRole(str, Enum):
    """역할 (스펙 2.1)"""
    STAFF = "staff"       # 일반 직원
    OWNER = "owner"       # 사장님 — 근무 시 항상 마감, 주말 회피
    MANAGER = "manager"   # 점장 — 고용/연차는 정직원과 동일, 근무 시 항상 마감
    # 사장님의 "홀만 / 홀+주방" 구분(스펙 2.2 A/B)은 Position 으로 표현한다.
    #   A(홀만)  -> position = hall
    #   B(홀+주방) -> position = both


class LeaveRequestStatus(str, Enum):
    """연차 신청 상태 (스펙 3)"""
    REQUESTED = "requested"   # 직원이 신청함
    CONFIRMED = "confirmed"   # 사장님이 확정함


class TimeSlot(str, Enum):
    """근무 시간대 (스펙 4.1) — 필요 인원은 포지션 x 시간대로 세분화."""
    OPEN = "open"    # 오픈 O
    MID = "mid"      # 미들 M  (홀은 미들 없음)
    CLOSE = "close"  # 마감 C


class ScheduleStatus(str, Enum):
    """월 스케줄 상태 (스펙 6.1 / 7)"""
    DRAFT = "draft"          # 작성 중
    CONFIRMED = "confirmed"  # 확정 (QR 공유 대상)
