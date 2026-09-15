"""스케줄 시점(당월 기준) 제한 테스트.

  - 자동배치: 당월 포함 과거 금지, 다음 달부터 가능
  - 수동 수정: 과거(당월 이전)만 금지, 당월은 계속 가능
  - 직원 조회: 과거+당월+"공유됨" 다음달까지만. 그 이후는 공유 상태와
    무관하게 항상 차단 (안전장치)

"오늘"을 2026-09-10 으로 고정한다 -> 당월=9월, 다음달=10월, 그 다음=11월.
"""

from datetime import date

import app.api.routes_me as routes_me
import app.api.routes_schedule as routes_schedule
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

import app.database as dbmod
from app.models import DEFAULT_STORE_ID, Schedule

TODAY = date(2026, 9, 10)


@pytest.fixture(autouse=True)
def _fixed_today(monkeypatch):
    monkeypatch.setattr(routes_schedule, "_today", lambda: TODAY)
    monkeypatch.setattr(routes_me, "_today", lambda: TODAY)


def _mk_staff(client: TestClient, name: str) -> int:
    return client.post(
        "/api/staff",
        json={"name": name, "employment_type": "full_time", "position": "hall", "role": "staff"},
    ).json()["id"]


def _direct_persist_schedule(client: TestClient, year: int, month: int) -> None:
    """자동배치 시점 제한을 우회해서 (테스트용으로) 과거/당월 스케줄을 만든다.
    실제로는 이런 달의 스케줄이 이미 예전에 자동배치+수정을 거쳐 저장돼 있었다고
    가정 — 지금 다시 만드는 게 아니라 "이미 있는" 상태를 시뮬레이션."""
    with Session(dbmod.engine) as s:
        s.add(Schedule(store_id=DEFAULT_STORE_ID, year=year, month=month, status="draft"))
        s.commit()


# --- 1) 자동배치 시점 제한 ---------------------------------------------------


def test_auto_schedule_blocked_for_current_and_past_month(client: TestClient):
    _mk_staff(client, "직원A")

    # 당월(9월) — 막혀야 함
    cur = client.post("/api/schedule/auto", json={"year": 2026, "month": 9})
    assert cur.status_code == 400
    assert "자동배치" in cur.json()["detail"]

    # 과거(8월) — 막혀야 함
    past = client.post("/api/schedule/auto", json={"year": 2026, "month": 8})
    assert past.status_code == 400

    # 작년 — 당연히 막혀야 함
    last_year = client.post("/api/schedule/auto", json={"year": 2025, "month": 12})
    assert last_year.status_code == 400


def test_auto_schedule_allowed_from_next_month(client: TestClient):
    _mk_staff(client, "직원A")

    ok = client.post("/api/schedule/auto", json={"year": 2026, "month": 10})
    assert ok.status_code == 200, ok.text

    # 그 다음 달, 훨씬 뒤도 자동배치 자체는 제한 없음 (직원 노출만 별도로 제한됨).
    also_ok = client.post("/api/schedule/auto", json={"year": 2026, "month": 12})
    assert also_ok.status_code == 200, also_ok.text


# --- 2) 수동 수정 시점 제한 --------------------------------------------------


def test_manual_edit_blocked_for_past_month_only(client: TestClient):
    sid = _mk_staff(client, "직원A")

    # 과거(8월) 스케줄이 이미 있다고 가정 -> 수정 시도하면 막혀야 함.
    _direct_persist_schedule(client, 2026, 8)
    past_edit = client.patch(
        "/api/schedule/entries",
        json={
            "year": 2026,
            "month": 8,
            "changes": [{"staff_id": sid, "work_date": "2026-08-05", "work_code": "FO"}],
        },
    )
    assert past_edit.status_code == 400
    assert "수정" in past_edit.json()["detail"]


def test_manual_edit_allowed_for_current_month(client: TestClient):
    """당월(9월)은 자동배치는 막히지만, 수동 수정은 급한 변경 대응용으로 계속 가능."""
    sid = _mk_staff(client, "직원A")
    _direct_persist_schedule(client, 2026, 9)

    edit = client.patch(
        "/api/schedule/entries",
        json={
            "year": 2026,
            "month": 9,
            "changes": [{"staff_id": sid, "work_date": "2026-09-15", "work_code": "FC"}],
        },
    )
    assert edit.status_code == 200, edit.text
    row = next(r for r in edit.json()["rows"] if r["staff_id"] == sid)
    assert row["cells"]["2026-09-15"] == "FC"


def test_manual_edit_allowed_for_future_months(client: TestClient):
    sid = _mk_staff(client, "직원A")
    client.post("/api/schedule/auto", json={"year": 2026, "month": 10})

    edit = client.patch(
        "/api/schedule/entries",
        json={
            "year": 2026,
            "month": 10,
            "changes": [{"staff_id": sid, "work_date": "2026-10-05", "work_code": "BC"}],
        },
    )
    assert edit.status_code == 200, edit.text


# --- 3)+4) 직원 조회 범위 제한 + 2달 이상 미래 안전장치 ----------------------


def test_employee_can_see_shared_current_month(client: TestClient):
    sid = _mk_staff(client, "직원A")
    client.post("/api/public/staff-accounts/signup", json={"staff_id": sid, "pin": "1234"})
    pending = client.get("/api/staff-accounts/pending").json()
    account_id = next(p["account_id"] for p in pending if p["staff_id"] == sid)
    client.post(f"/api/staff-accounts/{account_id}/approve")
    token = client.post(
        "/api/public/staff-accounts/login", json={"staff_id": sid, "pin": "1234"}
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 당월(9월) 스케줄을 만들고 공유.
    _direct_persist_schedule(client, 2026, 9)
    client.post("/api/schedule/2026/9/share")

    res = client.get("/api/me/schedule/2026/9", headers=headers)
    assert res.status_code == 200


def test_employee_cannot_see_two_months_ahead_even_if_shared(client: TestClient):
    """사장님이 실수로 다음 달보다 더 먼 미래(11월)를 공유해도 직원 화면엔 안 보임 —
    공유 상태와 무관하게 항상 적용되는 안전장치."""
    sid = _mk_staff(client, "직원A")
    client.post("/api/public/staff-accounts/signup", json={"staff_id": sid, "pin": "1234"})
    pending = client.get("/api/staff-accounts/pending").json()
    account_id = next(p["account_id"] for p in pending if p["staff_id"] == sid)
    client.post(f"/api/staff-accounts/{account_id}/approve")
    token = client.post(
        "/api/public/staff-accounts/login", json={"staff_id": sid, "pin": "1234"}
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 11월(당월+2) 스케줄 자동배치 + 공유 — 관리자 입장에선 정상적으로 "공유됨".
    auto = client.post("/api/schedule/auto", json={"year": 2026, "month": 11})
    assert auto.status_code == 200
    share = client.post("/api/schedule/2026/11/share")
    assert share.status_code == 200

    # 관리자 화면 기준으로는 분명히 confirmed 상태.
    admin_view = client.get("/api/schedule", params={"year": 2026, "month": 11})
    assert admin_view.json()["status"] == "confirmed"

    # 그런데도 직원 쪽(로그인 후 본인/전체 조회) 은 전부 차단되어야 한다.
    assert client.get("/api/me/schedule/2026/11", headers=headers).status_code == 404
    assert client.get("/api/me/team-schedule/2026/11", headers=headers).status_code == 404


def test_employee_can_see_next_month_only_when_shared(client: TestClient):
    sid = _mk_staff(client, "직원A")
    client.post("/api/public/staff-accounts/signup", json={"staff_id": sid, "pin": "1234"})
    pending = client.get("/api/staff-accounts/pending").json()
    account_id = next(p["account_id"] for p in pending if p["staff_id"] == sid)
    client.post(f"/api/staff-accounts/{account_id}/approve")
    token = client.post(
        "/api/public/staff-accounts/login", json={"staff_id": sid, "pin": "1234"}
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/schedule/auto", json={"year": 2026, "month": 10})

    # 공유 전엔 다음 달이어도 안 보임.
    assert client.get("/api/me/schedule/2026/10", headers=headers).status_code == 404

    client.post("/api/schedule/2026/10/share")
    assert client.get("/api/me/schedule/2026/10", headers=headers).status_code == 200
    assert client.get("/api/me/team-schedule/2026/10", headers=headers).status_code == 200
