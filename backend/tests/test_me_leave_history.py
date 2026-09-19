"""직원용 "내 연차" — 내 부여 이력·사용 이력만, 로그인한 직원 본인 것만."""

from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session

import app.database as dbmod
from app.models import DEFAULT_STORE_ID, MonthlyLeavePlan
from tests.test_me import _auth, _signup_and_approve


def _grant(client: TestClient, staff_id: int, days: float, granted_at: str, note: str):
    res = client.post(
        "/api/leave/grants",
        json={"staff_id": staff_id, "days": days, "granted_at": granted_at, "note": note},
    )
    assert res.status_code == 201, res.text


def test_leave_history_requires_staff_token(client: TestClient):
    assert client.get("/api/me/leave-grants").status_code == 401
    assert client.get("/api/me/leave-usages").status_code == 401


def test_my_grants_are_own_only_and_newest_first(client: TestClient):
    me_id, token = _signup_and_approve(client, "부여조회")
    other_id, _ = _signup_and_approve(client, "다른직원")
    _grant(client, me_id, 1, "2026-08-01", "월차 자동부여")
    _grant(client, me_id, 15, "2026-09-01", "1주년 연차부여")
    _grant(client, other_id, 3, "2026-09-02", "남의 부여")

    res = client.get("/api/me/leave-grants", headers=_auth(token))
    assert res.status_code == 200
    rows = [(g["granted_at"], g["days"], g["note"]) for g in res.json()]
    assert rows == [("2026-09-01", 15, "1주년 연차부여"), ("2026-08-01", 1, "월차 자동부여")]


def test_my_usages_are_own_only(client: TestClient):
    me_id, token = _signup_and_approve(client, "사용조회")
    other_id, _ = _signup_and_approve(client, "다른직원2")
    with Session(dbmod.engine) as s:
        for sid, days in [(me_id, 2), (other_id, 5)]:
            s.add(
                MonthlyLeavePlan(
                    store_id=DEFAULT_STORE_ID,
                    staff_id=sid,
                    year=2026,
                    month=10,
                    days=days,
                    remaining_after=10 - days,
                    applied_at=date(2026, 9, 20),
                )
            )
        s.commit()

    res = client.get("/api/me/leave-usages", headers=_auth(token))
    assert res.status_code == 200
    rows = res.json()
    assert [(r["staff_id"], r["days"], r["year_month"]) for r in rows] == [(me_id, 2, "2026-10")]
