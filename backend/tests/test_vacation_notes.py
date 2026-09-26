"""휴가 일정 공유 메모판 — 순수 참고용, 정직원·점장만 참여, 본인 것만 저장."""

from datetime import date

import app.api.routes_me as routes_me
from fastapi.testclient import TestClient

from app.services.vacation_window import window_months
from tests.test_me import _auth, _signup_and_approve


def _fix_today(monkeypatch, d: date):
    monkeypatch.setattr(routes_me, "_today", lambda: d)


def test_window_rolls_from_this_month_to_2027_12():
    # 2026년 11월 전에는 11월부터
    ms = window_months(date(2026, 9, 26))
    assert ms[0] == "2026-11" and ms[-1] == "2027-12" and len(ms) == 14
    assert window_months(date(2027, 3, 1))[0] == "2027-03"
    # 2027년 말이 가까워져도 최소 12개월은 보여준다 (연도 하드코딩으로 화면이 비지 않게)
    later = window_months(date(2027, 11, 3))
    assert later[0] == "2027-11" and len(later) == 12


def test_requires_staff_token(client: TestClient):
    assert client.get("/api/me/vacation-notes").status_code == 401
    assert client.put("/api/me/vacation-notes/mine", json={}).status_code == 401


def test_save_upsert_and_visible_to_others(client: TestClient, monkeypatch):
    _fix_today(monkeypatch, date(2026, 9, 26))
    a, ta = _signup_and_approve(client, "가나")
    _, tb = _signup_and_approve(client, "다라", role="manager")

    res = client.put(
        "/api/me/vacation-notes/mine",
        headers=_auth(ta),
        json={
            "months": ["2026-11", "2027-02"],
            "ranges": [
                {"start": "2026-11-12", "end": "2026-11-13"},
                {"start": "2026-11-14", "end": "2026-11-15"},  # 붙어 있으면 합쳐진다
            ],
            "memo": "  가족 여행  ",
        },
    )
    assert res.status_code == 200
    assert res.json()["ranges"] == [{"start": "2026-11-12", "end": "2026-11-15"}]
    assert res.json()["memo"] == "가족 여행"

    # 다시 저장하면 덮어쓴다 (행은 1개)
    client.put(
        "/api/me/vacation-notes/mine", headers=_auth(ta), json={"months": ["2026-12"]}
    )

    board = client.get("/api/me/vacation-notes", headers=_auth(tb)).json()
    assert board["months"][0] == "2026-11" and board["months"][-1] == "2027-12"
    assert board["can_edit"] is True
    assert [(n["staff_id"], n["months"], n["memo"]) for n in board["notes"]] == [
        (a, ["2026-12"], "")
    ]

    # 관리자 화면도 같은 데이터 (my_staff_id 없음)
    admin = client.get("/api/vacation-notes").json()
    assert admin["my_staff_id"] is None and len(admin["notes"]) == 1


def test_empty_save_deletes_row(client: TestClient, monkeypatch):
    _fix_today(monkeypatch, date(2026, 9, 26))
    _, t = _signup_and_approve(client, "비움")
    client.put("/api/me/vacation-notes/mine", headers=_auth(t), json={"no_plans": True})
    assert len(client.get("/api/vacation-notes").json()["notes"]) == 1
    res = client.put("/api/me/vacation-notes/mine", headers=_auth(t), json={})
    assert res.status_code == 200 and res.json() is None
    assert client.get("/api/vacation-notes").json()["notes"] == []


def test_validation(client: TestClient, monkeypatch):
    _fix_today(monkeypatch, date(2026, 9, 26))
    _, t = _signup_and_approve(client, "검증")
    put = lambda body: client.put("/api/me/vacation-notes/mine", headers=_auth(t), json=body)
    assert put({"months": ["2026-08"]}).status_code == 400  # 지난 달
    assert put({"months": ["2026-10"]}).status_code == 400  # 11월 이전
    assert put({"months": ["2028-01"]}).status_code == 400  # 범위 밖
    assert put({"months": ["2026-11"], "ranges": [{"start": "2026-11-30", "end": "2026-12-02"}]}).status_code == 400
    assert put({"months": ["2026-11"], "ranges": [{"start": "2026-12-01", "end": "2026-12-02"}]}).status_code == 400
    ok = put({"months": ["2026-11"], "no_plans": True, "memo": "가" * 80})
    assert ok.status_code == 200
    assert ok.json()["no_plans"] is False  # 달을 골랐으면 "일정 없음"은 무시
    assert len(ok.json()["memo"]) == 60


def test_part_time_and_owner_cannot_write_or_appear(client: TestClient, monkeypatch):
    _fix_today(monkeypatch, date(2026, 9, 26))
    _, tp = _signup_and_approve(client, "알바", employment_type="part_time")
    _, to = _signup_and_approve(client, "사장", role="owner")
    for t in (tp, to):
        assert client.get("/api/me/vacation-notes", headers=_auth(t)).json()["can_edit"] is False
        res = client.put("/api/me/vacation-notes/mine", headers=_auth(t), json={"months": ["2026-11"]})
        assert res.status_code == 403


def test_past_months_hidden_and_deleted_staff_excluded(client: TestClient, monkeypatch):
    _fix_today(monkeypatch, date(2026, 9, 26))
    sid, t = _signup_and_approve(client, "지남")
    _, t2 = _signup_and_approve(client, "퇴사")
    client.put("/api/me/vacation-notes/mine", headers=_auth(t), json={"months": ["2026-11", "2027-01"]})
    client.put("/api/me/vacation-notes/mine", headers=_auth(t2), json={"months": ["2026-11"]})
    sid2 = client.get("/api/me", headers=_auth(t2)).json()["id"]
    client.delete(f"/api/staff/{sid2}")

    _fix_today(monkeypatch, date(2026, 12, 1))
    notes = client.get("/api/vacation-notes").json()["notes"]
    assert [(n["staff_id"], n["months"]) for n in notes] == [(sid, ["2027-01"])]
