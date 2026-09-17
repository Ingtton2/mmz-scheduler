"""
주방 로테이션 미리보기/저장 API 데이터 형태.

  GET /api/kitchen-rotation?year=&month=  전월 기준 자동 계산(이미 저장돼 있으면 그 값) 반환
  PUT /api/kitchen-rotation               사장님이 확인/수정한 값을 그 달 기준으로 저장
"""

from pydantic import BaseModel, Field


class KitchenRotationItem(BaseModel):
    staff_id: int
    staff_name: str
    position: str = Field(pattern="^(open|mid|close)$")


class KitchenRotationPreview(BaseModel):
    year: int
    month: int
    items: list[KitchenRotationItem]
    saved: bool  # 이미 이 달 값으로 저장된 적 있으면 True, 아니면 방금 계산만 한 미리보기


class KitchenRotationPutItem(BaseModel):
    staff_id: int
    position: str = Field(pattern="^(open|mid|close)$")


class KitchenRotationPut(BaseModel):
    year: int
    month: int
    items: list[KitchenRotationPutItem]
