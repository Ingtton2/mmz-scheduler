"""
KitchenRotationAssignment = 주방 오픈/미들/마감 3인 로테이션의 "그 달 담당" 기록.

매달 1행씩 (직원별) 생성 — 전월 담당을 한 칸씩 이동(오픈→미들→마감→오픈)해서 자동
계산하고, 사장님이 자동배치 실행 전에 화면에서 확인 후 수동으로 덮어쓸 수 있다.
자동배치가 다음 달 로테이션을 계산할 때도 이 표의 "그 달" 행을 전월 기준으로 쓴다
(그날 실제로 근무했는지와 무관하게, 그 달의 "기본 담당"을 그대로 기준으로 삼음).
"""

from sqlmodel import Field, SQLModel, UniqueConstraint


class KitchenRotationAssignment(SQLModel, table=True):
    __tablename__ = "kitchen_rotation_assignment"
    __table_args__ = (
        UniqueConstraint("store_id", "year", "month", "staff_id", name="uq_rotation_cell"),
    )

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)

    year: int
    month: int
    staff_id: int = Field(foreign_key="staff.id", index=True)
    position: str  # "open" / "mid" / "close"
