"""
'스키마' = 화면과 서버가 주고받는 데이터의 형태 정의.

models(DB 저장용) 와 분리해두면, 내부 저장 구조를 바꿔도
화면과의 약속(API)이 안 깨집니다.
"""

from app.schemas.dayoff import DayOffRequestCreate, DayOffRequestRead
from app.schemas.leave import (
    LeaveBalanceInput,
    LeaveBalanceRead,
    LeaveRequestCreate,
    LeaveRequestRead,
    LeaveRequestUpdate,
)
from app.schemas.schedule import (
    AutoScheduleRequest,
    ManualEditRequest,
    PublicScheduleResult,
    ScheduleResult,
    ScheduleStaffRow,
    ScheduleWarningOut,
    ShareResult,
    ShiftSummary,
)
from app.schemas.staff import StaffCreate, StaffRead, StaffUpdate
from app.schemas.staffing import StaffingRequirementItem, StaffingRequirementsPut

__all__ = [
    "AutoScheduleRequest",
    "DayOffRequestCreate",
    "DayOffRequestRead",
    "LeaveBalanceInput",
    "LeaveBalanceRead",
    "LeaveRequestCreate",
    "LeaveRequestRead",
    "LeaveRequestUpdate",
    "ManualEditRequest",
    "PublicScheduleResult",
    "ScheduleResult",
    "ScheduleStaffRow",
    "ScheduleWarningOut",
    "ShareResult",
    "ShiftSummary",
    "StaffCreate",
    "StaffRead",
    "StaffUpdate",
    "StaffingRequirementItem",
    "StaffingRequirementsPut",
]
