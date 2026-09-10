"""
데이터베이스에 표가 잘 만들어졌는지 눈으로 확인하는 도구.

실행 (backend 폴더에서):
    .venv/bin/python scripts/show_db.py

출력:
  1) 만들어진 표 목록 + 각 표의 줄 수
  2) 직원(staff) 표 내용 (한글 라벨로)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # backend/ 를 import 경로에 추가

from sqlalchemy import inspect  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

import app.models  # noqa: F401, E402  (표 등록)
from app.database import engine, init_db
from app.models import Staff

LABELS = {
    "full_time": "정직원", "part_time": "파트타임",
    "hall": "홀 전담", "kitchen": "주방 전담", "both": "겸직",
    "staff": "일반 직원", "owner": "사장님",
    None: "-",
}


def main() -> None:
    init_db()  # 표가 없으면 만들고 시작

    insp = inspect(engine)
    tables = insp.get_table_names()

    print("=" * 50)
    print(f"DB 파일: {engine.url}")
    print(f"만들어진 표: {len(tables)}개")
    print("=" * 50)

    with Session(engine) as session:
        for name in sorted(tables):
            rows = session.connection().exec_driver_sql(f"SELECT COUNT(*) FROM {name}").scalar()
            cols = [c["name"] for c in insp.get_columns(name)]
            print(f"\n[{name}]  줄 수: {rows}")
            print("  칸(컬럼):", ", ".join(cols))

        print("\n" + "=" * 50)
        print("직원 표 내용")
        print("=" * 50)
        staff_rows = session.exec(select(Staff)).all()
        if not staff_rows:
            print("  (아직 등록된 직원 없음)")
        for s in staff_rows:
            active = "재직" if s.is_active else "퇴사"
            emp = LABELS.get(s.employment_type, s.employment_type) or "-"
            line = (
                f"  #{s.id}  {s.name}  |  {emp}"
                f"  |  {LABELS.get(s.position, s.position)}"
                f"  |  {LABELS.get(s.role, s.role)}"
                f"  |  {active}"
            )
            print(line)


if __name__ == "__main__":
    main()
