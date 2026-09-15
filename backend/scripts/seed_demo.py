"""
표준 테스트용 직원 명단으로 DB 를 초기화한다.

실행 (backend 폴더에서):
    .venv/bin/python scripts/seed_demo.py

하는 일:
  1) 이 매장의 직원 / 연차 / 필요인원 / 스케줄 데이터를 모두 지움 (매장 레코드는 유지)
  2) 아래 10명 명단을 새로 넣음
  3) 요일별 필요 인원을 홀 오픈1·마감1 / 주방 오픈1·미들1·마감2 (매일) 로 세팅

직원 명단:
  이태희 / 홀 겸 주방 / 사장
  박재영 / 홀 겸 주방 / 사장
  신주민 / 홀 겸 주방 / 점장  (정직원, 근무일은 마감 고정)
  정지원 / 홀        / 파트타임 (토·일 고정, 풀오마)
  김시윤 / 홀 전담   / 정직원
  윤재훈 / 홀 겸 주방 / 정직원
  권현석·이도경·윤용상·이희명 / 주방 전담 / 정직원
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, delete, select  # noqa: E402

from app.database import engine, init_db  # noqa: E402
from app.models import (  # noqa: E402
    DEFAULT_STORE_ID,
    LeaveBalance,
    LeaveRequest,
    Schedule,
    ScheduleEntry,
    Staff,
    StaffingRequirement,
)

ALL_WEEKDAYS = "0,1,2,3,4,5,6"

# (이름, 포지션, 역할, 고용형태, 근무요일, 고정여부, 기본휴무, 표시순서)
# 표시순서: 스케줄 표에서의 줄 순서 (작을수록 위). 사장(owner)은 항상 맨 아래로 따로 묶인다.
ROSTER = [
    ("신주민", "both", "manager", "full_time", ALL_WEEKDAYS, False, 8, 1),
    ("권현석", "kitchen", "staff", "full_time", ALL_WEEKDAYS, False, 8, 2),
    ("윤재훈", "both", "staff", "full_time", ALL_WEEKDAYS, False, 8, 3),
    ("이희명", "kitchen", "staff", "full_time", ALL_WEEKDAYS, False, 8, 4),
    ("김시윤", "hall", "staff", "full_time", ALL_WEEKDAYS, False, 8, 5),
    ("이도경", "kitchen", "staff", "full_time", ALL_WEEKDAYS, False, 8, 6),
    ("윤용상", "kitchen", "staff", "full_time", ALL_WEEKDAYS, False, 8, 7),
    ("정지원", "hall", "staff", "part_time", "5,6", True, 0, 8),
    ("이태희", "both", "owner", None, ALL_WEEKDAYS, False, 0, 1),
    ("박재영", "both", "owner", None, ALL_WEEKDAYS, False, 0, 2),
]

# 포지션 -> {슬롯: 최소인원}  (홀은 미들 없음)
REQUIREMENTS = {
    "hall": {"open": 1, "close": 1},
    "kitchen": {"open": 1, "mid": 1, "close": 2},
}


def main() -> None:
    init_db()
    with Session(engine) as s:
        # 1) 기존 데이터 삭제 (자식 -> 부모 순서)
        s.exec(delete(ScheduleEntry))
        s.exec(
            delete(Schedule).where(Schedule.store_id == DEFAULT_STORE_ID)
        )
        s.exec(
            delete(LeaveRequest).where(LeaveRequest.store_id == DEFAULT_STORE_ID)
        )
        s.exec(
            delete(LeaveBalance).where(LeaveBalance.store_id == DEFAULT_STORE_ID)
        )
        s.exec(
            delete(StaffingRequirement).where(
                StaffingRequirement.store_id == DEFAULT_STORE_ID
            )
        )
        s.exec(delete(Staff).where(Staff.store_id == DEFAULT_STORE_ID))
        s.commit()

        # 2) 직원 넣기
        for name, pos, role, emp, wd, fixed, off, order in ROSTER:
            staff = Staff(
                store_id=DEFAULT_STORE_ID,
                name=name,
                position=pos,
                role=role,
                employment_type=emp,
                work_weekdays=wd,
                fixed_schedule=fixed,
                sort_order=order,
            )
            s.add(staff)
            s.commit()
            s.refresh(staff)
            # 정직원 + 점장(정직원) 은 연차·기본휴무 잔액 행 생성
            if role in ("staff", "manager") and emp == "full_time":
                s.add(
                    LeaveBalance(
                        store_id=DEFAULT_STORE_ID,
                        staff_id=staff.id,
                        base_off_days=off,
                    )
                )
        s.commit()

        # 3) 요일별 필요 인원 (포지션 x 슬롯)
        for w in range(7):
            for pos, slots in REQUIREMENTS.items():
                for slot, cnt in slots.items():
                    s.add(
                        StaffingRequirement(
                            store_id=DEFAULT_STORE_ID,
                            weekday=w,
                            time_slot=slot,
                            position=pos,
                            min_headcount=cnt,
                        )
                    )
        s.commit()

        n = len(s.exec(select(Staff).where(Staff.store_id == DEFAULT_STORE_ID)).all())
        print(f"완료: 직원 {n}명, 필요 인원 홀 O1·C1 / 주방 O1·M1·C2 (매일)")
        print("자동배치는 화면(/admin/schedule)이나 아래로 실행:")
        print("  curl -s -X POST localhost:8000/api/schedule/auto -H 'Content-Type: application/json' -d '{\"year\":2026,\"month\":10}'")


if __name__ == "__main__":
    main()
