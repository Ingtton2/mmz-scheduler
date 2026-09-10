"""
WorkCode = 근무 코드 (스펙 2.3, 10.2).

O, M, C, 홀오픈, 풀오픈, D/O, 연차, && 등.
'이 매장 전용 설정값'이므로 하드코딩하지 않고 표로 저장하여
사장님이 설정 화면에서 이름/시간대/색상을 직접 정의·수정할 수 있게 함.
"""

from sqlmodel import Field, SQLModel


class WorkCode(SQLModel, table=True):
    __tablename__ = "work_code"

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)

    code: str                      # 표에 표시되는 짧은 코드. 예: "O", "홀오픈", "&&"
    label: str                     # 뜻. 예: "오픈", "홀 전담 오픈"
    start_time: str | None = None  # "HH:MM". 휴무/연차는 None
    end_time: str | None = None
    color: str = "#e5e7eb"         # 스케줄표 셀 배경색 (hex)
    is_work: bool = True           # 실제 근무면 True, 휴무/연차면 False
    is_owner_code: bool = False    # 사장님 근무 코드(&&) 여부
    sort_order: int = 0            # 표시 순서
