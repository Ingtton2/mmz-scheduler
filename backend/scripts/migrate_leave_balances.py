"""
[일회성] 연차 데이터 이관 스크립트 (스펙 3, 6단계).

옛 구조("전월잔여연차" + "전월발생연차" = 합연차, 합연차 - 사용 = 잔여연차)를
새 구조(부여연차(누적) - 사용연차(누적) = 잔여연차)로 옮긴다.

  새 부여연차 = (부여 이력으로 이미 받은 값이 있다면 그것) + (옛 전월잔여연차 + 옛 전월발생연차)
  사용연차는 이름·의미가 그대로라 손대지 않는다.
  잔여연차(부여 - 사용)는 이관 전후로 값이 같아야 한다 — 아래에서 직원별로 비교해서 보여준다.

이관마다 "연차 관리 > 연차 사용 현황 > 부여 이력"에 "기존 데이터 이관" 한 줄을 남긴다.
그 기록이 있는 직원은 다시 실행해도 건너뛰므로, 여러 번 실행해도 안전하다(idempotent).

실행 (backend 폴더에서):
    .venv/bin/python scripts/migrate_leave_balances.py
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # backend/ 를 import 경로에 추가

from sqlalchemy import text  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

import app.models  # noqa: F401, E402  (표 등록)
from app.database import engine  # noqa: E402
from app.models import DEFAULT_STORE_ID, LeaveBalance, LeaveGrantLog, Staff  # noqa: E402

MIGRATION_NOTE = "기존 데이터 이관"


def _read_old_columns() -> dict[int, tuple[float, float, float]]:
    """staff_id -> (전월잔여연차, 전월발생연차, 사용연차).
    이 컬럼들은 이제 SQLModel 클래스엔 없지만 표에는 그대로 남아있어서 raw SQL로 읽는다."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT staff_id, prev_remaining, prev_accrued, used FROM leave_balance")
        ).all()
    return {r[0]: (r[1] or 0.0, r[2] or 0.0, r[3] or 0.0) for r in rows}


def main() -> None:
    old = _read_old_columns()

    with Session(engine) as session:
        balances = session.exec(select(LeaveBalance)).all()
        staff_names = {s.id: s.name for s in session.exec(select(Staff)).all()}
        already_migrated = {
            g.staff_id
            for g in session.exec(
                select(LeaveGrantLog).where(LeaveGrantLog.note == MIGRATION_NOTE)
            ).all()
        }

        header = f"{'직원':<10} {'이관 전 잔여연차':>14} {'이관 후 잔여연차':>14}  결과"
        print(header)
        print("-" * len(header))

        migrated = 0
        skipped = 0
        for bal in balances:
            name = staff_names.get(bal.staff_id, f"(#{bal.staff_id})")
            prev_remaining, prev_accrued, used = old.get(bal.staff_id, (0.0, 0.0, 0.0))
            old_total = round(prev_remaining + prev_accrued, 2)
            before_remaining = round(old_total - used, 2)

            if bal.staff_id in already_migrated:
                after_remaining = round(bal.granted - bal.used, 2)
                print(f"{name:<10} {before_remaining:>14} {after_remaining:>14}  이미 이관됨")
                skipped += 1
                continue

            bal.granted = round(bal.granted + old_total, 2)
            session.add(bal)
            session.add(
                LeaveGrantLog(
                    store_id=DEFAULT_STORE_ID,
                    staff_id=bal.staff_id,
                    granted_at=date.today(),
                    days=old_total,
                    note=MIGRATION_NOTE,
                )
            )
            after_remaining = round(bal.granted - bal.used, 2)
            ok = before_remaining == after_remaining
            print(
                f"{name:<10} {before_remaining:>14} {after_remaining:>14}  "
                + ("일치" if ok else "!! 불일치 확인 필요")
            )
            migrated += 1

        session.commit()
        print("-" * len(header))
        print(f"이번에 이관: {migrated}명 · 이미 이관되어 건너뜀: {skipped}명 · 전체: {len(balances)}명")


if __name__ == "__main__":
    main()
