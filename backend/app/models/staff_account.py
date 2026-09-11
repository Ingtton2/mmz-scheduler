"""
직원 셀프서비스 계정 (스펙 9). Staff 1명당 계정 0~1개.

- 로그인은 이메일/전화번호가 아니라 "매장 안에서 이름 선택 + 4자리 PIN" 방식이라,
  별도의 독립적인 사용자 테이블 대신 이 표 하나로 Staff 에 계정 정보를 매단다.
- status: pending(가입 신청, 사장님 승인 대기) / approved(정식 멤버, 로그인 가능)
  거절되면 이 행을 아예 지운다 (재신청 가능하게).
- 사장님(role=owner) 이 가입하면 승인 대기 없이 즉시 approved 로 만든다
  (스스로가 승인권자이므로 대기 목록을 거칠 필요가 없음 — 스펙 9).
"""

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class StaffAccount(SQLModel, table=True):
    __tablename__ = "staff_account"

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)
    staff_id: int = Field(foreign_key="staff.id", unique=True, index=True)

    pin_hash: str
    status: str = "pending"  # pending | approved
    must_change_pin: bool = False  # 사장님이 PIN 초기화한 뒤 true (다음 로그인 때 새 PIN 강제)

    created_at: datetime = Field(default_factory=utcnow)
    approved_at: datetime | None = None
