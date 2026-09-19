"""저장된 근무표를 다시 열거나 칸을 고칠 때도 인원 부족/초과 경고를 다시 계산한다."""

from datetime import date

from fastapi.testclient import TestClient

from app.services.headcount_check import check_headcount

REQ = {wd: {"hall": {"open": 1, "close": 1}, "kitchen": {"open": 1, "mid": 1, "close": 2}} for wd in range(7)}
DAY = "2026-10-05"


def _cells(codes: dict[int, str]) -> dict[int, dict[str, str]]:
    return {sid: {DAY: c} for sid, c in codes.items()}


def test_exact_headcount_has_no_warning():
    cells = _cells({1: "FO", 2: "FC", 3: "BO", 4: "BM", 5: "BC", 6: "BC"})
    assert check_headcount([DAY], cells, {}, REQ) == []


def test_seventh_person_triggers_excess_warning():
    cells = _cells({1: "FO", 2: "FC", 3: "BO", 4: "BM", 5: "BC", 6: "BC", 7: "BM"})
    out = check_headcount([DAY], cells, {}, REQ)
    assert [w.position for w in out] == ["총원"]
    assert out[0].needed == 6 and out[0].filled == 7


def test_missing_slot_triggers_shortage_warning():
    cells = _cells({1: "FO", 2: "FC", 3: "BO", 4: "BM", 5: "BC"})  # 주방 마감 1명 모자람
    out = check_headcount([DAY], cells, {}, REQ)
    assert any(w.position == "주방·마감" and w.needed == 2 and w.filled == 1 for w in out)


def test_part_time_full_shift_covers_all_slots_of_its_position():
    cells = _cells({9: "풀오마", 3: "BO", 4: "BM", 5: "BC", 6: "BC"})
    assert check_headcount([DAY], cells, {9: "hall"}, REQ) == []


def test_empty_schedule_gives_no_warnings():
    assert check_headcount([DAY], {1: {}}, {}, REQ) == []


def test_saved_schedule_warns_after_manual_edit_adds_extra_person(client: TestClient, monkeypatch):
    import app.api.routes_schedule as routes_schedule

    monkeypatch.setattr(routes_schedule, "_today", lambda: date(2026, 9, 10))
    ids = []
    for name, pos in (("홀A", "hall"), ("홀B", "hall"), ("주1", "kitchen"), ("주2", "kitchen"), ("주3", "kitchen")):
        ids.append(
            client.post(
                "/api/staff",
                json={"name": name, "position": pos, "role": "staff", "employment_type": "full_time",
                      "leave": {"base_off_days": 8}},
            ).json()["id"]
        )
    items = []
    for wd in range(7):
        items += [
            {"weekday": wd, "position": "hall", "time_slot": "open", "min_headcount": 1},
            {"weekday": wd, "position": "hall", "time_slot": "close", "min_headcount": 1},
        ]
    client.put("/api/staffing-requirements", json={"items": items})
    body = client.post("/api/schedule/auto", json={"year": 2026, "month": 10}).json()

    # 홀 필요인원(오픈1+마감1=2명)이 이미 채워진 날, 쉬는 사람(D/O) 한 명을 추가 근무로 바꿔서
    # 총원이 필요인원을 넘게 만든다 (배치 결과는 솔버마다 달라서 조건에 맞는 날을 찾는다).
    work = {"FO", "FC", "BO", "BM", "BC", "풀오마"}
    day, rest = next(
        (d, next(r for r in body["rows"] if r["cells"][d] == "D/O"))
        for d in body["days"]
        if sum(1 for r in body["rows"] if r["cells"][d] in work) >= 2
        and any(r["cells"][d] == "D/O" for r in body["rows"])
    )
    res = client.patch(
        "/api/schedule/entries",
        json={"year": 2026, "month": 10, "changes": [
            {"staff_id": rest["staff_id"], "work_date": day, "work_code": "FO"},
        ]},
    )
    assert res.status_code == 200
    warnings = res.json()["warnings"]
    assert any(w["date"] == day for w in warnings), warnings
    assert client.get("/api/schedule", params={"year": 2026, "month": 10}).json()["warnings"] == warnings


def test_all_managers_and_owners_off_triggers_warning():
    """사장님 둘 + 점장이 같은 날 모두 쉬면(수기 수정 등) 관리 책임자 경고."""
    cells = _cells({1: "FO", 2: "FC", 3: "BO", 4: "BM", 5: "BC", 6: "BC", 10: "D/O", 11: "D/O", 12: "연차"})
    out = check_headcount([DAY], cells, {}, REQ, manager_group_ids={10, 11, 12})
    mgr = [w for w in out if w.position == "관리책임자"]
    assert len(mgr) == 1 and mgr[0].date == DAY


def test_one_manager_group_member_working_is_fine():
    cells = _cells({1: "FO", 2: "FC", 3: "BO", 4: "BM", 5: "BC", 6: "BC", 10: "D/O", 11: "D/O", 12: "BC"})
    out = check_headcount([DAY], cells, {}, REQ, manager_group_ids={10, 11, 12})
    assert not [w for w in out if w.position == "관리책임자"]
