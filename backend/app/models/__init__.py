"""
데이터베이스 표(테이블) 정의 모음.

이 파일이 모든 모델 모듈을 불러오므로, 다른 곳에서는
`import app.models` 한 줄이면 SQLModel 이 모든 표를 인식합니다.

표 목록 (자세한 밑그림: docs/architecture.md 4번):
  Store               매장
  Staff               직원
  WorkCode            근무 코드 (매장별 커스텀)
  LeaveBalance        직원 연차 정보
  LeaveRequest        직원 연차 신청
  DayOffRequest       직원 사전 휴무 신청 (연차와 별개, 월 20일)
  StaffingRequirement 요일·시간대별 필요 인원
  Schedule            월 스케줄 (공유코드 = QR 대상)
  ScheduleEntry       스케줄 한 칸
"""

from app.models.enums import (
    EmploymentType,
    LeaveRequestStatus,
    Position,
    ScheduleStatus,
    StaffRole,
    TimeSlot,
)
from app.models.dayoff import MAX_PER_MONTH, DayOffRequest
from app.models.leave import LeaveBalance, LeaveRequest
from app.models.schedule import Schedule, ScheduleEntry
from app.models.staff import Staff
from app.models.staff_account import StaffAccount
from app.models.staffing import StaffingRequirement
from app.models.store import DEFAULT_STORE_ID, Store
from app.models.work_code import WorkCode

__all__ = [
    "DEFAULT_STORE_ID",
    "MAX_PER_MONTH",
    "DayOffRequest",
    "EmploymentType",
    "LeaveBalance",
    "LeaveRequest",
    "LeaveRequestStatus",
    "Position",
    "Schedule",
    "ScheduleEntry",
    "ScheduleStatus",
    "Staff",
    "StaffAccount",
    "StaffRole",
    "StaffingRequirement",
    "Store",
    "TimeSlot",
    "WorkCode",
]
