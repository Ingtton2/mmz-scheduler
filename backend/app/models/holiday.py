"""
Holiday = 매장에 등록한 공휴일(대체공휴일 포함) 날짜.

한국 공휴일은 매년 날짜가 바뀌고 임시공휴일도 수시로 생겨 자동 계산 대신
관리자가 직접 날짜를 등록한다. 스케줄표 표시 용도 외에, 자동배치의 "정직원·
점장 휴무일수 공정성"(주말+공휴일 기준, engine.py) 계산에도 쓰인다.
"""

from datetime import date as date_

from sqlmodel import Field, SQLModel


class Holiday(SQLModel, table=True):
    __tablename__ = "holiday"

    id: int | None = Field(default=None, primary_key=True)
    store_id: int = Field(foreign_key="store.id", index=True)

    # 필드명이 `date` 타입 이름과 겹치면 SQLModel 이 클래스 생성 시 어노테이션을
    # 잘못 해석하는 문제가 있어, import 를 date_ 로 별칭 처리했다.
    date: date_ = Field(index=True)
    name: str
