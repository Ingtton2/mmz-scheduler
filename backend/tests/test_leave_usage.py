"""연차 부여/사용 현황 API 테스트 (스펙 3, "연차 관리 > 연차 사용 현황" 탭)."""

from datetime import date

from fastapi.testclient import TestClient


def _make_staff(client: TestClient, name: str, hire_date: str | None = None) -> int:
    payload = {
        "name": name,
        "employment_type": "full_time",
        "position": "both",
        "role": "staff",
    }
    if hire_date is not None:
        payload["hire_date"] = hire_date
    return client.post("/api/staff", json=payload).json()["id"]


def _months_ago(n: int) -> str:
    d = date.today()
    total = d.month - 1 - n
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, 28)  # 말일 문제 피하려고 28일로 고정
    return date(year, month, day).isoformat()


def test_grant_increases_balance_and_logs(client: TestClient):
    sid = _make_staff(client, "부여테스트")
    res = client.post(
        "/api/leave/grants", json={"staff_id": sid, "days": 15, "note": "1주년 연차부여"}
    )
    assert res.status_code == 201, res.text
    assert res.json()["days"] == 15

    staff = next(s for s in client.get("/api/staff").json() if s["id"] == sid)
    assert staff["leave"]["granted"] == 15
    assert staff["leave"]["remaining"] == 15

    log = client.get("/api/leave/grant-log").json()
    assert any(g["staff_id"] == sid and g["days"] == 15 for g in log)


def test_grant_candidates_monthly_and_anniversary(client: TestClient):
    monthly_sid = _make_staff(client, "월차대상", hire_date=_months_ago(3))
    anniv_sid = _make_staff(client, "1주년대상", hire_date=_months_ago(12))
    # 20개월 전 입사자는 1~12개월째 기념일이 전부 지나서 이번 달엔 해당 없음.
    none_sid = _make_staff(client, "해당없음", hire_date=_months_ago(20))

    candidates = client.get("/api/leave/grant-candidates").json()
    by_id = {c["staff_id"]: c for c in candidates}

    assert by_id[monthly_sid]["kind"] == "monthly"
    assert by_id[monthly_sid]["days"] == 1
    assert by_id[anniv_sid]["kind"] == "anniversary"
    assert by_id[anniv_sid]["days"] == 15
    assert none_sid not in by_id


def test_granting_removes_from_candidates_this_month(client: TestClient):
    sid = _make_staff(client, "부여후제외", hire_date=_months_ago(3))
    candidates = client.get("/api/leave/grant-candidates").json()
    assert any(c["staff_id"] == sid for c in candidates)

    client.post("/api/leave/grants", json={"staff_id": sid, "days": 1, "note": "월차 자동부여"})

    candidates = client.get("/api/leave/grant-candidates").json()
    assert not any(c["staff_id"] == sid for c in candidates)
