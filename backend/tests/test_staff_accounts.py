"""직원 셀프서비스 계정: 가입/승인/거절/로그인/PIN 초기화 (스펙 9)."""

from fastapi.testclient import TestClient


def _make_staff(client: TestClient, name: str, role: str = "staff", **kw) -> int:
    payload = {
        "name": name,
        "employment_type": kw.pop("employment_type", "full_time"),
        "position": kw.pop("position", "hall"),
        "role": role,
    }
    if role == "owner":
        payload.pop("employment_type")
    payload.update(kw)
    return client.post("/api/staff", json=payload).json()["id"]


def test_signup_pending_then_approve_then_login(client: TestClient):
    sid = _make_staff(client, "김가입")

    # 아직 계정 없는 사람 목록에 있어야 함
    avail = client.get("/api/public/staff-accounts/available").json()
    assert sid in [a["id"] for a in avail]

    res = client.post(
        "/api/public/staff-accounts/signup", json={"staff_id": sid, "pin": "1234"}
    )
    assert res.status_code == 201
    assert res.json()["status"] == "pending"

    # 신청 후엔 available 목록에서 빠짐
    avail2 = client.get("/api/public/staff-accounts/available").json()
    assert sid not in [a["id"] for a in avail2]

    # 승인 전엔 로그인 불가
    bad = client.post("/api/public/staff-accounts/login", json={"staff_id": sid, "pin": "1234"})
    assert bad.status_code == 401

    # 승인 대기 목록에 있어야 함
    pending = client.get("/api/staff-accounts/pending").json()
    account_id = next(p["account_id"] for p in pending if p["staff_id"] == sid)

    approve = client.post(f"/api/staff-accounts/{account_id}/approve")
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    # 로그인 화면 목록에 나타남
    loginable = client.get("/api/public/staff-accounts/login-list").json()
    assert sid in [s["id"] for s in loginable]

    # 틀린 PIN 은 거부
    wrong = client.post("/api/public/staff-accounts/login", json={"staff_id": sid, "pin": "0000"})
    assert wrong.status_code == 401

    # 올바른 PIN 로그인 성공
    ok = client.post("/api/public/staff-accounts/login", json={"staff_id": sid, "pin": "1234"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["staff"]["name"] == "김가입"
    assert body["must_change_pin"] is False
    assert body["token"]


def test_duplicate_signup_rejected(client: TestClient):
    sid = _make_staff(client, "중복가입")
    client.post("/api/public/staff-accounts/signup", json={"staff_id": sid, "pin": "1111"})
    dup = client.post("/api/public/staff-accounts/signup", json={"staff_id": sid, "pin": "2222"})
    assert dup.status_code == 409


def test_invalid_pin_format_rejected(client: TestClient):
    sid = _make_staff(client, "핀형식")
    res = client.post("/api/public/staff-accounts/signup", json={"staff_id": sid, "pin": "12"})
    assert res.status_code == 422
    res2 = client.post(
        "/api/public/staff-accounts/signup", json={"staff_id": sid, "pin": "abcd"}
    )
    assert res2.status_code == 422


def test_owner_signup_auto_approved(client: TestClient):
    oid = _make_staff(client, "사장님계정", role="owner", position="both")
    res = client.post("/api/public/staff-accounts/signup", json={"staff_id": oid, "pin": "9999"})
    assert res.status_code == 201
    assert res.json()["status"] == "approved"

    # 승인 대기 목록엔 안 뜸 (이미 승인됨)
    pending = client.get("/api/staff-accounts/pending").json()
    assert oid not in [p["staff_id"] for p in pending]

    # 바로 로그인 가능
    ok = client.post("/api/public/staff-accounts/login", json={"staff_id": oid, "pin": "9999"})
    assert ok.status_code == 200


def test_reject_removes_and_allows_resignup(client: TestClient):
    sid = _make_staff(client, "거절될사람")
    client.post("/api/public/staff-accounts/signup", json={"staff_id": sid, "pin": "1234"})
    pending = client.get("/api/staff-accounts/pending").json()
    account_id = next(p["account_id"] for p in pending if p["staff_id"] == sid)

    assert client.post(f"/api/staff-accounts/{account_id}/reject").status_code == 204

    # 다시 available 목록에 나타나고, 재신청 가능
    avail = client.get("/api/public/staff-accounts/available").json()
    assert sid in [a["id"] for a in avail]
    again = client.post(
        "/api/public/staff-accounts/signup", json={"staff_id": sid, "pin": "5678"}
    )
    assert again.status_code == 201


def test_reset_pin_forces_change(client: TestClient):
    sid = _make_staff(client, "핀초기화")
    client.post("/api/public/staff-accounts/signup", json={"staff_id": sid, "pin": "1234"})
    pending = client.get("/api/staff-accounts/pending").json()
    account_id = next(p["account_id"] for p in pending if p["staff_id"] == sid)
    client.post(f"/api/staff-accounts/{account_id}/approve")

    reset = client.post(f"/api/staff-accounts/reset-pin/{sid}")
    assert reset.status_code == 200
    temp_pin = reset.json()["temp_pin"]
    assert len(temp_pin) == 4 and temp_pin.isdigit()

    # 옛 PIN 은 더는 안 통함
    old = client.post("/api/public/staff-accounts/login", json={"staff_id": sid, "pin": "1234"})
    assert old.status_code == 401

    # 임시 PIN 으로 로그인하면 must_change_pin=True
    login = client.post(
        "/api/public/staff-accounts/login", json={"staff_id": sid, "pin": temp_pin}
    )
    assert login.status_code == 200
    assert login.json()["must_change_pin"] is True
