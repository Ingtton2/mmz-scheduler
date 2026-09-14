"""자동배치 엔진 테스트 (스펙 5 우선순위: 연차 / 관리책임자 / 인원 / 포지션 / 사장·점장 / 공정성)."""

from datetime import date

from fastapi.testclient import TestClient

from app.scheduler.engine import (
    CODE_BC,
    CODE_BLOCKED,
    CODE_BM,
    CODE_BO,
    CODE_FC,
    CODE_FO,
    CODE_FULL,
    CODE_LEAVE,
    CODE_OFF,
    WORK_CODES,
    SolveInput,
    StaffInput,
    build_schedule,
)

WORK = set(WORK_CODES)
OPENS = {CODE_FO, CODE_BO}
CLOSES = {CODE_FC, CODE_BC}
HALL = {CODE_FO, CODE_FC}
KITCHEN = {CODE_BO, CODE_BM, CODE_BC}

# 홀 오픈1·마감1 / 주방 오픈1·미들1·마감2
BASIC = {
    wd: {
        "hall": {"open": 1, "close": 1},
        "kitchen": {"open": 1, "mid": 1, "close": 2},
    }
    for wd in range(7)
}
HALL_OC = {wd: {"hall": {"open": 1, "close": 1}} for wd in range(7)}


def _n(cells: dict[str, str], *codes: str) -> int:
    cs = set(codes)
    return sum(1 for v in cells.values() if v in cs)


def _base_team():
    """홀2 + 겸직2 + 주방5 정직원 (BASIC 요건을 정직원만으로 커버 가능)."""
    return [
        StaffInput(1, "홀A", "hall", min_days_off=8),
        StaffInput(2, "홀B", "hall", min_days_off=8),
        StaffInput(3, "겸직A", "both", min_days_off=8),
        StaffInput(4, "겸직B", "both", min_days_off=8),
        StaffInput(5, "주1", "kitchen", min_days_off=8),
        StaffInput(6, "주2", "kitchen", min_days_off=8),
        StaffInput(7, "주3", "kitchen", min_days_off=8),
        StaffInput(8, "주4", "kitchen", min_days_off=8),
        StaffInput(9, "주5", "kitchen", min_days_off=8),
    ]


def test_fills_all_position_slots():
    r = build_schedule(SolveInput(2026, 9, _base_team(), requirements=BASIC))
    assert r.feasible is True
    assert r.warnings == []


def test_hall_staff_never_get_mid():
    staff = _base_team()
    r = build_schedule(SolveInput(2026, 9, staff, requirements=BASIC))
    for sid in (1, 2):  # 홀 전담
        assert _n(r.entries[sid], CODE_BM) == 0


def test_leave_is_locked():
    staff = _base_team()
    leave = {1: {date(2026, 9, 3), date(2026, 9, 10)}}
    r = build_schedule(SolveInput(2026, 9, staff, leave_dates=leave, requirements=BASIC))
    assert r.entries[1]["2026-09-03"] == CODE_LEAVE
    assert r.entries[1]["2026-09-10"] == CODE_LEAVE


def test_shortage_warning_not_failure():
    staff = [StaffInput(1, "홀A", "hall")]
    r = build_schedule(SolveInput(2026, 9, staff, requirements=HALL_OC))
    assert r.feasible is False
    assert any("마감" in w.position for w in r.warnings)


def test_part_time_gets_full_day_code():
    staff = _base_team() + [
        StaffInput(
            10, "알바", "hall", work_weekdays=frozenset({5, 6}), fixed=True,
            is_part_time=True,
        )
    ]
    r = build_schedule(SolveInput(2026, 9, staff, requirements=BASIC))
    weekend = [
        v
        for k, v in r.entries[10].items()
        if date.fromisoformat(k).weekday() >= 5
    ]
    assert weekend and all(v == CODE_FULL for v in weekend)
    # 평일은 근무 안 함
    assert all(
        r.entries[10][k] == CODE_OFF
        for k in r.entries[10]
        if date.fromisoformat(k).weekday() < 5
    )


def test_owner_and_manager_always_close():
    staff = _base_team() + [
        StaffInput(10, "사장", "both", role="owner"),
        StaffInput(11, "점장", "both", role="manager", min_days_off=8),
    ]
    r = build_schedule(SolveInput(2026, 9, staff, requirements=BASIC))
    for sid in (10, 11):
        worked = [v for v in r.entries[sid].values() if v in WORK]
        assert worked, f"{sid} 근무 0일 (테스트 설정 문제)"
        assert all(v in CLOSES for v in worked), f"{sid} 마감 아닌 근무 있음"


def test_manager_group_min_one_per_day():
    # 사장2 + 점장1. 매일 최소 1명 출근해야 함 (하드)
    staff = _base_team() + [
        StaffInput(10, "사장A", "both", role="owner"),
        StaffInput(11, "사장B", "hall", role="owner"),
        StaffInput(12, "점장", "both", role="manager", min_days_off=8),
    ]
    r = build_schedule(SolveInput(2026, 9, staff, requirements=BASIC))
    for day in r.days:
        on = sum(1 for sid in (10, 11, 12) if r.entries[sid][day] in WORK)
        assert on >= 1, f"{day} 관리 책임자 3명 모두 쉼"


def test_manager_group_all_on_leave_warns():
    staff = _base_team() + [
        StaffInput(10, "사장A", "both", role="owner"),
        StaffInput(11, "사장B", "hall", role="owner"),
        StaffInput(12, "점장", "both", role="manager", min_days_off=8),
    ]
    d = date(2026, 9, 15)
    leave = {10: {d}, 11: {d}, 12: {d}}
    r = build_schedule(SolveInput(2026, 9, staff, leave_dates=leave, requirements=BASIC))
    assert any("관리 책임자" in w.message for w in r.warnings)
    assert r.feasible is False


def test_owner_weekend_minimized():
    # 관리책임자 = 사장2 + 점장1. 주말 최소1인은 점장이 커버 -> 사장 주말근무는 거의 0
    staff = _base_team() + [
        StaffInput(10, "사장A", "both", role="owner"),
        StaffInput(11, "사장B", "hall", role="owner"),
        StaffInput(12, "점장", "both", role="manager"),
    ]
    r = build_schedule(SolveInput(2026, 9, staff, requirements=BASIC))
    for oid in (10, 11):
        wknd = sum(
            1
            for k, v in r.entries[oid].items()
            if v in WORK and date.fromisoformat(k).weekday() >= 5
        )
        assert wknd <= 2, f"사장 {oid} 주말근무 {wknd}일"


def test_days_off_pinned_to_target():
    staff = _base_team()
    r = build_schedule(SolveInput(2026, 9, staff, requirements=BASIC))
    if r.feasible:
        for s in staff:
            assert _n(r.entries[s.id], CODE_OFF) == 8, s.name


def _assert_base_off_respected(r, staff, month_days: int):
    """정직원·점장은 (D/O + 사휴) == 기본휴무, 근무일수 == 전체 - 기본휴무 - 연차."""
    assert r.feasible, [w.message for w in r.warnings]
    for s in staff:
        if s.min_days_off <= 0:
            continue
        su = r.shift_summary[s.id]
        assert su["off"] + su["blocked"] == s.min_days_off, (
            s.name,
            su,
        )
        assert su["work"] == month_days - s.min_days_off - su["leave"], (s.name, su)


def test_base_days_off_hard_for_regulars_and_manager():
    # 일반 정직원 9 + 점장 1 + 사장 1. 전원 기본휴무 8일이 지켜져야 함.
    staff = _base_team() + [
        StaffInput(20, "점장", "both", role="manager", min_days_off=8),
        StaffInput(21, "사장", "both", role="owner"),
    ]
    r = build_schedule(SolveInput(2026, 9, staff, requirements=BASIC))
    _assert_base_off_respected(r, [s for s in staff if s.min_days_off > 0], 30)


def test_manager_not_underworked_when_close_only():
    # 버그 재현: 점장은 마감 고정이라 마감 슬롯을 정직원과 나눠 씀.
    # 관리책임자 = 사장2 + 점장1 이라 매일 1명만 있으면 됨 -> 점장이 매일 강제되진 않음.
    # 그래도 점장의 기본휴무 8일(=근무 22일)이 지켜져야 한다.
    staff = _base_team() + [
        StaffInput(20, "점장", "both", role="manager", min_days_off=8),
        StaffInput(21, "사장A", "both", role="owner"),
        StaffInput(22, "사장B", "hall", role="owner"),
    ]
    r = build_schedule(SolveInput(2026, 9, staff, requirements=BASIC))
    assert r.feasible, [w.message for w in r.warnings]
    su = r.shift_summary[20]
    assert su["work"] == 22 and su["off"] == 8, su


def test_base_days_off_with_leave_and_blocked():
    staff = _base_team() + [
        StaffInput(20, "점장", "both", role="manager", min_days_off=8)
    ]
    leave = {5: {date(2026, 9, d) for d in (2, 3, 4)}}       # 주1 연차 3일
    blk = {20: {date(2026, 9, d) for d in (7, 14, 21, 28)}}  # 점장 사전휴무 4일
    r = build_schedule(
        SolveInput(
            2026, 9, staff, leave_dates=leave, blocked_dates=blk, requirements=BASIC
        )
    )
    if not r.feasible:
        return
    # 주1: 근무 30-8-3=19, D/O 8
    assert r.shift_summary[5]["work"] == 19
    assert r.shift_summary[5]["off"] == 8
    # 점장: 근무 30-8=22 유지 (사휴 4 + D/O 4 = 8)
    assert r.shift_summary[20]["work"] == 22
    assert r.shift_summary[20]["blocked"] == 4
    assert r.shift_summary[20]["off"] == 4


def test_days_off_unmeetable_warns_and_flags_infeasible():
    # 점장 기본휴무 2일인데 사전휴무 4일 -> 근무일수를 못 맞춤 -> 경고 + feasible False
    staff = _base_team() + [
        StaffInput(20, "점장", "both", role="manager", min_days_off=2)
    ]
    blk = {20: {date(2026, 9, d) for d in (5, 12, 19, 26)}}
    r = build_schedule(
        SolveInput(2026, 9, staff, blocked_dates=blk, requirements=BASIC)
    )
    assert r.feasible is False
    assert any(
        "근무" in w.message and "점장" in w.message for w in r.warnings
    ), [w.message for w in r.warnings]


def test_leave_not_counted_toward_days_off():
    staff = _base_team()
    leave = {5: {date(2026, 9, d) for d in (1, 2, 3, 4, 5)}}
    r = build_schedule(SolveInput(2026, 9, staff, leave_dates=leave, requirements=BASIC))
    c = r.entries[5]
    assert _n(c, CODE_LEAVE) == 5
    if r.feasible:
        assert _n(c, CODE_OFF) == 8


def test_blocked_dates_hard_and_keep_workdays():
    staff = _base_team()
    blk = {3: {date(2026, 9, 10), date(2026, 9, 11), date(2026, 9, 12)}}
    r = build_schedule(
        SolveInput(2026, 9, staff, blocked_dates=blk, requirements=BASIC)
    )
    if not r.feasible:
        return
    c = r.entries[3]
    for d in ("2026-09-10", "2026-09-11", "2026-09-12"):
        assert c[d] == CODE_BLOCKED
    su = r.shift_summary[3]
    assert su["blocked"] == 3
    assert su["work"] == 30 - 8            # 근무일수 유지 (연차와 달리 안 줄어듦)
    assert su["off"] == 8 - 3              # 사전휴무가 D/O 예산을 잠식


def test_blocked_vs_leave_workdays():
    staff = _base_team()
    days3 = {5: {date(2026, 9, d) for d in (10, 11, 12)}}
    r_lv = build_schedule(
        SolveInput(2026, 9, staff, leave_dates=days3, requirements=BASIC)
    )
    r_bk = build_schedule(
        SolveInput(2026, 9, staff, blocked_dates=days3, requirements=BASIC)
    )
    if r_lv.feasible and r_bk.feasible:
        assert r_lv.shift_summary[5]["work"] == 30 - 8 - 3   # 연차: 근무일 줄어듦
        assert r_bk.shift_summary[5]["work"] == 30 - 8       # 사전휴무: 유지


def test_open_close_fair_among_regulars():
    staff = _base_team()
    r = build_schedule(SolveInput(2026, 9, staff, requirements=BASIC))
    if not r.feasible:
        return
    # 같은 포지션 그룹끼리 오픈/마감 횟수 편차가 작아야 한다
    for pos in ("hall", "both", "kitchen"):
        ids = [s.id for s in staff if s.position == pos]
        opens = [r.shift_summary[i]["open"] for i in ids]
        closes = [r.shift_summary[i]["close"] for i in ids]
        assert max(opens) - min(opens) <= 3, (pos, opens)
        assert max(closes) - min(closes) <= 3, (pos, closes)


def _max_streak(cells: dict[str, str]) -> int:
    best = run = 0
    for _k, v in sorted(cells.items()):
        run = run + 1 if v in WORK else 0
        best = max(best, run)
    return best


def test_no_6day_streak_when_slack():
    # 여유가 충분하면 6일 이상 연속 근무가 없어야 한다
    staff = _base_team() + [
        StaffInput(20, "점장", "both", role="manager", min_days_off=8),
        StaffInput(21, "사장A", "both", role="owner"),
        StaffInput(22, "사장B", "both", role="owner"),
    ]
    r = build_schedule(SolveInput(2026, 9, staff, requirements=BASIC))
    assert r.feasible
    for s in staff:
        assert _max_streak(r.entries[s.id]) <= 5, (
            s.name,
            _max_streak(r.entries[s.id]),
        )
    assert not any("연속 근무" in w.message for w in r.warnings)


def test_6day_streak_allowed_with_warning_when_tight():
    # 홀 전담 1명뿐인데 홀 오픈/마감 각 1 필요 -> 그 사람이 매일 나와야 함 -> 긴 연속근무
    staff = [
        StaffInput(1, "홀A", "hall"),           # min_days_off 0 -> 근무일수 제한 없음
        StaffInput(2, "주1", "kitchen"),
        StaffInput(3, "주2", "kitchen"),
        StaffInput(4, "주3", "kitchen"),
    ]
    r = build_schedule(SolveInput(2026, 9, staff, requirements=BASIC))
    # 자동배치는 멈추지 않는다
    assert r.entries  # 결과가 나옴
    assert _max_streak(r.entries[1]) >= 6
    assert any("연속 근무" in w.message and "홀A" in w.message for w in r.warnings)


def test_codes_reveal_position():
    # 홀 전담 -> FO/FC 만, 주방 전담 -> BO/BM/BC 만, 겸직 -> 그날 코드가 배정 포지션과 일치
    staff = _base_team()
    r = build_schedule(SolveInput(2026, 9, staff, requirements=BASIC))
    assert r.feasible
    for sid in (1, 2):  # 홀 전담
        for c in r.entries[sid].values():
            assert c not in KITCHEN, (sid, c)
    for sid in (5, 6, 7, 8, 9):  # 주방 전담
        for c in r.entries[sid].values():
            assert c not in HALL, (sid, c)
    for sid in (3, 4):  # 겸직: 코드가 홀/주방 둘 다 나올 수 있고, summary 와 일치
        su = r.shift_summary[sid]
        hall_codes = _n(r.entries[sid], *HALL)
        kit_codes = _n(r.entries[sid], *KITCHEN)
        assert hall_codes == su["hall"] and kit_codes == su["kitchen"]


def test_owner_both_prefers_hall_close():
    # 겸직 사장은 마감 시 홀(FC) 우선. 주방은 홀이 충분하고 주방이 부족할 때만.
    staff = _base_team() + [
        StaffInput(20, "사장A", "both", role="owner"),
        StaffInput(21, "사장B", "hall", role="owner"),
        StaffInput(22, "점장", "both", role="manager"),
    ]
    r = build_schedule(SolveInput(2026, 9, staff, requirements=BASIC))
    su = r.shift_summary[20]
    if su["work"] > 0:
        assert su["hall"] >= su["kitchen"], su  # 홀 위주


def test_fixed_schedule_forces_work():
    staff = _base_team() + [
        StaffInput(
            10, "고정", "hall", work_weekdays=frozenset({5, 6}), fixed=True,
            is_part_time=True,
        )
    ]
    leave = {10: {date(2026, 9, 6)}}
    r = build_schedule(SolveInput(2026, 9, staff, leave_dates=leave, requirements=BASIC))
    for day, code in r.entries[10].items():
        d = date.fromisoformat(day)
        if d == date(2026, 9, 6):
            assert code == CODE_LEAVE
        elif d.weekday() in (5, 6):
            assert code == CODE_FULL
        else:
            assert code == CODE_OFF


# --- API 통합 ---


def _mk(client: TestClient, name: str, position: str, role: str = "staff",
        emp: str | None = "full_time") -> int:
    body = {"name": name, "position": position, "role": role}
    if emp:
        body["employment_type"] = emp
    return client.post("/api/staff", json=body).json()["id"]


def test_auto_schedule_endpoint(client: TestClient, monkeypatch):
    import app.api.routes_schedule as routes_schedule

    # 2026-10 을 "다음 달"로 취급하도록 오늘을 고정 (자동배치 시점 제한 대비).
    monkeypatch.setattr(routes_schedule, "_today", lambda: date(2026, 9, 10))

    _mk(client, "홀A", "hall")
    _mk(client, "겸직A", "both")
    _mk(client, "주1", "kitchen")
    _mk(client, "주2", "kitchen")
    _mk(client, "주3", "kitchen")
    _mk(client, "점장A", "both", role="manager")

    items = []
    for wd in range(7):
        items += [
            {"weekday": wd, "position": "hall", "time_slot": "open", "min_headcount": 1},
            {"weekday": wd, "position": "hall", "time_slot": "close", "min_headcount": 1},
            {"weekday": wd, "position": "kitchen", "time_slot": "open", "min_headcount": 1},
            {"weekday": wd, "position": "kitchen", "time_slot": "close", "min_headcount": 1},
        ]
    assert client.put("/api/staffing-requirements", json={"items": items}).status_code == 200

    res = client.post("/api/schedule/auto", json={"year": 2026, "month": 10})
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["days"]) == 31
    # 점장은 근무일이 전부 마감(C)
    mgr = next(r for r in body["rows"] if r["staff_name"] == "점장A")
    assert mgr["summary"]["open"] == 0 and mgr["summary"]["mid"] == 0
