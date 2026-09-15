"""직원 등록/수정/삭제 + 연차 정보 + 근무 가능 요일 API 테스트."""

from fastapi.testclient import TestClient


def test_fulltime_has_leave_parttime_does_not(client: TestClient):
    ft = client.post(
        "/api/staff",
        json={
            "name": "정직원A",
            "employment_type": "full_time",
            "position": "hall",
            "role": "staff",
            "leave": {"prev_remaining": 3, "prev_accrued": 1.5, "used": 2},
        },
    ).json()
    assert ft["leave"] is not None
    assert ft["leave"]["total_accrued"] == 4.5
    assert ft["leave"]["remaining"] == 2.5

    pt = client.post(
        "/api/staff",
        json={
            "name": "파트타임A",
            "employment_type": "part_time",
            "position": "kitchen",
            "role": "staff",
            "leave": {"prev_remaining": 10},  # 넣어도 무시됨
        },
    ).json()
    assert pt["leave"] is None

    owner = client.post(
        "/api/staff",
        json={"name": "사장님", "position": "both", "role": "owner"},
    ).json()
    assert owner["leave"] is None


def test_patch_leave_rejected_for_parttime(client: TestClient):
    pid = client.post(
        "/api/staff",
        json={
            "name": "알바수정불가",
            "employment_type": "part_time",
            "position": "hall",
            "role": "staff",
        },
    ).json()["id"]
    res = client.patch(
        f"/api/staff/{pid}/leave",
        json={"base_off_days": 0, "prev_remaining": 1, "prev_accrued": 1, "used": 0},
    )
    assert res.status_code == 400


def test_patch_leave_recomputes_for_fulltime(client: TestClient):
    sid = client.post(
        "/api/staff",
        json={
            "name": "정직원B",
            "employment_type": "full_time",
            "position": "kitchen",
            "role": "staff",
        },
    ).json()["id"]
    res = client.patch(
        f"/api/staff/{sid}/leave",
        json={"base_off_days": 0, "prev_remaining": 5, "prev_accrued": 2, "used": 3},
    )
    assert res.status_code == 200
    assert res.json()["leave"]["total_accrued"] == 7
    assert res.json()["leave"]["remaining"] == 4


def test_work_weekdays_default_and_custom(client: TestClient):
    full = client.post(
        "/api/staff",
        json={
            "name": "풀타임요일",
            "employment_type": "full_time",
            "position": "hall",
            "role": "staff",
        },
    ).json()
    assert full["work_weekdays"] == [0, 1, 2, 3, 4, 5, 6]
    assert full["fixed_schedule"] is False

    part = client.post(
        "/api/staff",
        json={
            "name": "주말알바",
            "employment_type": "part_time",
            "position": "hall",
            "role": "staff",
            "work_weekdays": [5, 6],
            "fixed_schedule": True,
        },
    ).json()
    assert part["work_weekdays"] == [5, 6]
    assert part["fixed_schedule"] is True


def test_patch_staff_updates_weekdays(client: TestClient):
    sid = client.post(
        "/api/staff",
        json={
            "name": "요일수정",
            "employment_type": "part_time",
            "position": "hall",
            "role": "staff",
            "work_weekdays": [5, 6],
        },
    ).json()["id"]
    res = client.patch(
        f"/api/staff/{sid}", json={"work_weekdays": [0, 2, 4], "fixed_schedule": True}
    )
    assert res.status_code == 200
    assert res.json()["work_weekdays"] == [0, 2, 4]
    assert res.json()["fixed_schedule"] is True


def test_empty_weekdays_rejected(client: TestClient):
    res = client.post(
        "/api/staff",
        json={
            "name": "요일없음",
            "employment_type": "part_time",
            "position": "hall",
            "role": "staff",
            "work_weekdays": [],
        },
    )
    assert res.status_code == 422


def test_staff_requires_employment_type(client: TestClient):
    res = client.post(
        "/api/staff",
        json={"name": "고용형태없음", "position": "hall", "role": "staff"},
    )
    assert res.status_code == 422


def test_delete_hides_from_list(client: TestClient):
    sid = client.post(
        "/api/staff",
        json={
            "name": "삭제될사람",
            "employment_type": "full_time",
            "position": "hall",
            "role": "staff",
        },
    ).json()["id"]
    assert client.delete(f"/api/staff/{sid}").status_code == 204
    assert "삭제될사람" not in [s["name"] for s in client.get("/api/staff").json()]


def test_delete_preserves_leave_and_dayoff_history(client: TestClient):
    """직원 삭제(is_active=False)는 목록에서만 숨기고, 연차/사전휴무 이력은
    그대로 남아 있어야 한다 (급여 정산·과거 스케줄 조회 대비 — 스펙 6.1)."""
    sid = client.post(
        "/api/staff",
        json={
            "name": "이력보존직원",
            "employment_type": "full_time",
            "position": "hall",
            "role": "staff",
        },
    ).json()["id"]
    client.post(
        "/api/leave-requests",
        json={"staff_id": sid, "start_date": "2026-11-10", "end_date": "2026-11-10"},
    )
    client.post(
        "/api/dayoff-requests",
        json={"staff_id": sid, "start_date": "2026-11-20", "end_date": "2026-11-20"},
    )

    assert client.delete(f"/api/staff/{sid}").status_code == 204

    # 직원 목록에선 사라짐.
    assert "이력보존직원" not in [s["name"] for s in client.get("/api/staff").json()]

    # 그러나 연차/사전휴무 신청 기록은 이름과 함께 그대로 남아 있음 (하드 삭제 안 됨).
    leave_names = [r["staff_name"] for r in client.get("/api/leave-requests").json()]
    dayoff_names = [r["staff_name"] for r in client.get("/api/dayoff-requests").json()]
    assert "이력보존직원" in leave_names
    assert "이력보존직원" in dayoff_names


def test_hire_date_set_on_create_and_editable(client: TestClient):
    sid = client.post(
        "/api/staff",
        json={
            "name": "입사일직원",
            "employment_type": "full_time",
            "position": "hall",
            "role": "staff",
            "hire_date": "2024-03-02",
        },
    ).json()["id"]

    listed = client.get("/api/staff").json()
    row = next(s for s in listed if s["id"] == sid)
    assert row["hire_date"] == "2024-03-02"

    updated = client.patch(f"/api/staff/{sid}", json={"hire_date": "2025-01-15"})
    assert updated.status_code == 200
    assert updated.json()["hire_date"] == "2025-01-15"


def test_hire_date_defaults_to_null(client: TestClient):
    created = client.post(
        "/api/staff",
        json={"name": "입사일없음", "employment_type": "part_time", "position": "kitchen", "role": "staff"},
    ).json()
    assert created["hire_date"] is None
