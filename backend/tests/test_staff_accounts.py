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


def test_owner_signup_rejected(client: TestClient):
    """사장님은 셀프서비스 계정이 필요 없다 (어차피 관리자 화면을 그대로 씀) — 가입 자체가 막혀야 함."""
    oid = _make_staff(client, "사장님계정", role="owner", position="both")
    res = client.post("/api/public/staff-accounts/signup", json={"staff_id": oid, "pin": "9999"})
    assert res.status_code == 400

    # 로그인도 당연히 안 됨 (계정이 없으므로).
    login = client.post("/api/public/staff-accounts/login", json={"staff_id": oid, "pin": "9999"})
    assert login.status_code == 401


def test_owner_hidden_from_public_signup_list(client: TestClient):
    """사장님은 공개 가입 화면(/join)에 안 보여야 한다."""
    oid = _make_staff(client, "숨겨질사장님", role="owner", position="both")
    sid = _make_staff(client, "보일직원")

    avail = client.get("/api/public/staff-accounts/available").json()
    ids = [a["id"] for a in avail]
    assert oid not in ids
    assert sid in ids


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


def test_deleted_staff_disappears_from_account_lists(client: TestClient):
    """직원을 삭제(비활성화)하면 그 직원의 계정도 승인 대기/가입된 계정 목록에서
    빠져야 한다 (이력은 StaffAccount 행 자체는 남지만 화면엔 안 보임)."""
    sid = _make_staff(client, "삭제될가입자")
    client.post("/api/public/staff-accounts/signup", json={"staff_id": sid, "pin": "1234"})
    pending = client.get("/api/staff-accounts/pending").json()
    assert sid in [p["staff_id"] for p in pending]
    account_id = next(p["account_id"] for p in pending if p["staff_id"] == sid)
    client.post(f"/api/staff-accounts/{account_id}/approve")
    assert sid in [a["staff_id"] for a in client.get("/api/staff-accounts").json()]

    assert client.delete(f"/api/staff/{sid}").status_code == 204

    assert sid not in [a["staff_id"] for a in client.get("/api/staff-accounts").json()]
    assert sid not in [p["staff_id"] for p in client.get("/api/staff-accounts/pending").json()]

    # 로그인도 당연히 막혀야 함.
    login = client.post("/api/public/staff-accounts/login", json={"staff_id": sid, "pin": "1234"})
    assert login.status_code == 401
