"""
필요 인원 설정 API 데이터 형태 (스펙 4).

필요 인원은 "포지션 x 시간대" 로 세분화한다.
  - weekday: 0=월 ~ 6=일
  - position: "hall"(홀) / "kitchen"(주방)
  - time_slot: "open"(오픈) / "mid"(미들) / "close"(마감)   ※ 홀은 보통 미들 없음
  - min_headcount: 그 요일 그 슬롯에 필요한 최소 인원

저장은 "전체 교체" 방식: 화면이 전체 격자를 통째로 보내면 서버가 기존 걸 지우고 새로 넣는다.
"""

from pydantic import BaseModel, Field


class StaffingRequirementItem(BaseModel):
    weekday: int = Field(ge=0, le=6)
    position: str = Field(pattern="^(hall|kitchen)$")
    time_slot: str = Field(pattern="^(open|mid|close)$")
    min_headcount: int = Field(ge=0)


class StaffingRequirementsPut(BaseModel):
    items: list[StaffingRequirementItem]
