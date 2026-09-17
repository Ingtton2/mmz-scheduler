"""
자동배치 / 수동 수정 / 공유 API 데이터 형태 (스펙 5, 6.1, 7).
"""

from datetime import date, datetime

from pydantic import BaseModel, Field

# 수동 수정에서 허용하는 근무 코드
VALID_CODES = {
    "FO", "FC", "BO", "BM", "BC", "풀오마", "D/O", "연차", "사휴",
}


class AutoScheduleRequest(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class ScheduleWarningOut(BaseModel):
    date: str
    position: str
    needed: int
    filled: int
    message: str


class ShiftSummary(BaseModel):
    open: int = 0     # 오픈 (FO+BO)
    mid: int = 0      # 미들 (BM)
    close: int = 0    # 마감 (FC+BC)
    full: int = 0     # 풀오마 (파트타임)
    hall: int = 0     # 홀에서 근무한 일수 (FO/FC)
    kitchen: int = 0  # 주방에서 근무한 일수 (BO/BM/BC)
    off: int = 0      # D/O 휴무
    leave: int = 0    # 연차
    blocked: int = 0  # 사전 휴무 신청
    work: int = 0     # 실근무일


class ScheduleStaffRow(BaseModel):
    staff_id: int
    staff_name: str
    position: str
    role: str
    employment_type: str | None = None
    cells: dict[str, str]  # "YYYY-MM-DD" -> 근무코드
    summary: ShiftSummary = ShiftSummary()


class ScheduleResult(BaseModel):
    year: int
    month: int
    days: list[str]
    rows: list[ScheduleStaffRow]
    warnings: list[ScheduleWarningOut] = []
    feasible: bool = True
    solve_seconds: float = 0.0
    saved: bool = False
    edited: bool = False        # 수동 수정된 스케줄인지
    status: str = "draft"       # "draft"(임시) / "confirmed"(공유됨) — 직원 노출 여부를 가름
    share_code: str | None = None
    published_at: datetime | None = None  # 직원에게 공개(공유)한 시각. 재공유 때마다 갱신.
    generated_at: datetime | None = None


# --- 수동 수정 (스펙 6.1) ---


class ScheduleEdit(BaseModel):
    staff_id: int
    work_date: date
    work_code: str

    @property
    def valid(self) -> bool:
        return self.work_code in VALID_CODES


class ManualEditRequest(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    changes: list[ScheduleEdit]


# --- 공유 / 직원 조회 (스펙 7, 6.2) ---


class ShareResult(BaseModel):
    share_code: str
    published_at: datetime


class PublicRow(BaseModel):
    staff_name: str
    position: str
    role: str
    cells: dict[str, str]


class PublicScheduleResult(BaseModel):
    year: int
    month: int
    store_name: str
    days: list[str]
    rows: list[PublicRow]
    generated_at: datetime | None = None
