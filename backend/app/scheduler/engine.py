"""
⭐ 자동배치 엔진 (스펙 5).

우선순위(스펙 5) 순서로 구현:
  1. 연차 고정                신청한 연차 날짜엔 그 직원 배제 (하드)
  2. 관리 책임자 최소 1인 출근  사장님 2 + 점장 1 중 매일 1명 이상 (하드, 최우선)
  3. 필요 인원 채우기          포지션 x 시간대(오픈/미들/마감)별 최소 인원 (소프트 + 경고)
  4. 포지션 매칭              전담은 해당 포지션만, 겸직은 그 날 한쪽 (하드)
  4.5 정직원·점장 휴무 공정성  주말(토/일)+공휴일 기준으로, 정직원·점장 각자 총휴무일수
                             (D/O+연차+사전휴무)가 그 기간에 최소 2일 ~ 최대 4일 들어가도록
                             보장 (전원 똑같이 나누는 게 아니라 상·하한만 보장, 하드에 준함).
                             권장치는 3일 — 엔진이 스스로 배치하는 D/O는 웬만하면 3일에
                             맞추고, 4일까지 가는 건 "만든다"기보다 그 사람이 사전휴무·
                             연차를 주말·공휴일에 신청해서 하드로 이미 4일이 된 경우를
                             허용하는 것. 최소/최대 보장은 사장님 주말 회피(5번)보다
                             우선순위가 높음 — 필요하면 사장님을 주말에 투입해서라도
                             맞춘다 (권장치 선호는 사장님 주말 회피보다는 약하지만, 그 아래
                             소프트 규칙들보다는 강해서 실제로 3일에 잘 수렴한다).
  5. 사장님/점장 배치          근무 시 항상 마감(C) 고정. 사장님은 주말 회피(소프트,
                             단 4.5번 휴무 공정성에는 밀림).
  6. 공정성 (일반 직원만)      오픈/마감 몰아주기 방지 (소프트). 사장님·점장 제외.
  6.5 주방 로테이션 선호도     rotation_slot 이 있는 직원은 그 슬롯(오픈/미들/마감)에
                             우선 배정 (소프트). 연차/사전휴무로 못 나오면 그날만
                             다른 사람이 채우고 로테이션 자체는 안 깨짐.
  6.6 마감 백업 선호도         close_backup=True 인 직원은, 점장이 쉬는 날 주방 마감
                             자리를 우선 채움 (소프트).
  (+) 6일 이상 연속 근무 회피   소프트. 인원 부족으로 불가피하면 허용하고 경고.
  7. 부족분 경고              못 채워도 멈추지 않고 채운 만큼 + 경고

근무 코드 (홀/주방이 코드에 드러남 — 겸직 직원도 그날 포지션이 바로 보임):
  - 정직원  : 홀이면 FO/FC, 주방이면 BO/BM/BC (홀은 미들 없음)
  - 파트타임: 시간대 구분 없이 하루 전체 "풀오마" (그 포지션 모든 슬롯 커버)
  - 사장/점장: 항상 마감 → 홀이면 FC, 주방이면 BC (별도 코드 없음)

기술: OR-Tools CP-SAT. 소프트 제약은 슬랙으로 흡수.
"""

from __future__ import annotations

import calendar
import random
from dataclasses import dataclass, field
from datetime import date

from ortools.sat.python import cp_model

CODE_FO = "FO"   # 홀 오픈
CODE_FC = "FC"   # 홀 마감
CODE_BO = "BO"   # 주방 오픈
CODE_BM = "BM"   # 주방 미들
CODE_BC = "BC"   # 주방 마감
CODE_FULL = "풀오마"
CODE_OFF = "D/O"
CODE_LEAVE = "연차"
CODE_BLOCKED = "사휴"  # 사전 휴무 신청 (연차와 별개, 근무일수는 안 줄어듦)

# 코드 -> (슬롯, 포지션)
CODE_INFO = {
    CODE_FO: ("open", "hall"),
    CODE_FC: ("close", "hall"),
    CODE_BO: ("open", "kitchen"),
    CODE_BM: ("mid", "kitchen"),
    CODE_BC: ("close", "kitchen"),
}
WORK_CODES = frozenset({CODE_FO, CODE_FC, CODE_BO, CODE_BM, CODE_BC, CODE_FULL})

_SLOTS = ("open", "mid", "close")
_SLOT_LABEL = {"open": "오픈", "mid": "미들", "close": "마감"}
_POS_LABEL = {"hall": "홀", "kitchen": "주방"}


@dataclass
class StaffInput:
    id: int
    name: str
    position: str  # hall / kitchen / both
    role: str = "staff"  # staff / owner / manager
    work_weekdays: frozenset[int] = frozenset({0, 1, 2, 3, 4, 5, 6})
    fixed: bool = False           # 근무 가능 요일엔 항상 배치 (파트타임 고정 근무)
    min_days_off: int = 0         # 월 휴일(D/O) 목표. 연차 제외. 0=제한없음
    is_part_time: bool = False    # 파트타임 -> 풀오마 근무
    rotation_slot: str | None = None  # 이번 달 로테이션 기본 포지션 (open/mid/close). 소프트 선호도.
    close_backup: bool = False    # 점장 결근 시 주방 마감 자리를 우선 채울 백업 인원. 소프트 선호도.

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"

    @property
    def is_manager(self) -> bool:
        return self.role == "manager"

    @property
    def is_close_only(self) -> bool:
        """근무일이 항상 마감(C)인가? 사장님·점장."""
        return self.role in ("owner", "manager")

    @property
    def in_manager_group(self) -> bool:
        """관리 책임자 그룹(최소 1인 출근 대상)?"""
        return self.role in ("owner", "manager")

    @property
    def is_regular(self) -> bool:
        """공정성 대상 = 일반 정직원. 사장/점장/파트타임 제외."""
        return self.role == "staff" and not self.is_part_time and self.min_days_off > 0

    @property
    def in_offday_fair_group(self) -> bool:
        """휴무일수 공정성(주말+공휴일) 대상 = 정직원 + 점장. 사장/파트타임 제외."""
        return (
            self.role in ("staff", "manager")
            and not self.is_part_time
            and self.min_days_off > 0
        )


@dataclass
class SolveInput:
    year: int
    month: int
    staff: list[StaffInput]
    # 연차: 그 날 배치 금지 + 총 근무일수도 그만큼 줄어듦
    leave_dates: dict[int, set[date]] = field(default_factory=dict)
    # 이번 달 연차 사용 개수 (직원 id -> 개수). 날짜는 엔진이 "이미 쉬는 날" 중에서 고른다
    # (필요인원 부족을 만들지 않는 범위에서, 작은 랜덤 가중치로 흩뿌림). 근무일수는 그만큼 줄어듦.
    leave_counts: dict[int, int] = field(default_factory=dict)
    random_seed: int | None = None  # 연차 날짜 랜덤 선택용 (테스트에서 고정)
    # 사전 휴무 신청: 그 날 배치 금지 (하드), 총 근무일수는 유지 (다른 날로 채움)
    blocked_dates: dict[int, set[date]] = field(default_factory=dict)
    # 등록된 공휴일(대체공휴일 포함). 정직원·점장 휴무 공정성 계산(주말+공휴일
    # 기준)에만 쓰인다 — 그 외 배치 로직(필요인원 등)에는 영향 없음.
    holiday_dates: set[date] = field(default_factory=set)
    # weekday -> {position -> {slot -> min_headcount}}
    requirements: dict[int, dict[str, dict[str, int]]] = field(default_factory=dict)
    # 하루 총 출근 인원 목표 (요일 무관, 사장님·점장 포함). 0 = 비활성.
    # 포지션x슬롯 필요인원과 별개 규칙 — 파트타임이 하루 종일 근무하며 슬롯을
    # 여러 개 혼자 채워도, 실제 출근 "머릿수"는 이 값을 목표로 맞춘다 (소프트).
    daily_headcount_target: int = 0


@dataclass
class SolveWarning:
    date: str
    position: str
    needed: int
    filled: int
    message: str


@dataclass
class SolveResult:
    year: int
    month: int
    days: list[str]
    entries: dict[int, dict[str, str]] = field(default_factory=dict)
    shift_summary: dict[int, dict[str, int]] = field(default_factory=dict)
    warnings: list[SolveWarning] = field(default_factory=list)
    feasible: bool = True
    solve_seconds: float = 0.0
    leave_placed: dict[int, int] = field(default_factory=dict)  # 직원 id -> 실제 배치된 연차 개수


def _month_days(year: int, month: int) -> list[date]:
    n = calendar.monthrange(year, month)[1]
    return [date(year, month, d) for d in range(1, n + 1)]


def _req(inp: SolveInput, weekday: int, position: str, slot: str) -> int:
    return int(
        inp.requirements.get(weekday, {}).get(position, {}).get(slot, 0)
    )


def build_schedule(inp: SolveInput, *, time_limit_s: float = 12.0) -> SolveResult:
    days = _month_days(inp.year, inp.month)
    staff = inp.staff
    n_days = len(days)
    day_set = set(days)
    result = SolveResult(
        year=inp.year,
        month=inp.month,
        days=[d.isoformat() for d in days],
        entries={s.id: {} for s in staff},
        shift_summary={s.id: {} for s in staff},
    )

    if not staff:
        result.warnings.append(
            SolveWarning("", "", 0, 0, "등록된 직원이 없습니다. 먼저 직원을 등록하세요.")
        )
        result.feasible = False
        return result

    total_req = sum(
        _req(inp, wd, p, sl)
        for wd in range(7)
        for p in _POS_LABEL
        for sl in _SLOTS
    )
    if total_req == 0:
        result.warnings.append(
            SolveWarning(
                "", "", 0, 0,
                "필요 인원이 모두 0입니다. '필요 인원 설정'에서 값을 넣어주세요.",
            )
        )

    m = cp_model.CpModel()

    work: dict[tuple[int, int], cp_model.IntVar] = {}
    ah: dict[tuple[int, int], cp_model.IntVar] = {}   # 그 날 홀에 있음 (both 전용)
    ak: dict[tuple[int, int], cp_model.IntVar] = {}
    so: dict[tuple[int, int], cp_model.IntVar] = {}   # 정직원 오픈
    sm: dict[tuple[int, int], cp_model.IntVar] = {}   # 정직원 미들
    sc: dict[tuple[int, int], cp_model.IntVar] = {}   # 정직원 마감

    lv: dict[tuple[int, int], cp_model.IntVar] = {}   # 엔진이 고른 연차일 (이미 쉬는 날 중)
    rng = random.Random(inp.random_seed)

    for s in staff:
        off = inp.leave_dates.get(s.id, set())
        blk = inp.blocked_dates.get(s.id, set())
        for di, d in enumerate(days):
            w = m.NewBoolVar(f"w_{s.id}_{di}")
            work[(s.id, di)] = w
            available = d.weekday() in s.work_weekdays
            if d in off or d in blk or not available:
                m.Add(w == 0)  # 연차 / 사전 휴무 / 근무 불가 요일 -> 배치 금지
            elif s.fixed:
                m.Add(w == 1)
            elif inp.leave_counts.get(s.id, 0) > 0:
                v = m.NewBoolVar(f"lv_{s.id}_{di}")
                m.Add(v <= 1 - w)  # 쉬는 날에만 연차 라벨을 붙일 수 있음 -> 인원 부족일을 만들지 않음
                lv[(s.id, di)] = v

            if s.position == "both":
                h = m.NewBoolVar(f"ah_{s.id}_{di}")
                k = m.NewBoolVar(f"ak_{s.id}_{di}")
                m.Add(h + k == w)
                ah[(s.id, di)] = h
                ak[(s.id, di)] = k

            if not s.is_close_only and not s.is_part_time:
                o = m.NewBoolVar(f"so_{s.id}_{di}")
                mm = m.NewBoolVar(f"sm_{s.id}_{di}")
                c = m.NewBoolVar(f"sc_{s.id}_{di}")
                m.Add(o + mm + c == w)
                so[(s.id, di)] = o
                sm[(s.id, di)] = mm
                sc[(s.id, di)] = c

    def in_hall(s: StaffInput, di: int):
        if s.position == "hall":
            return work[(s.id, di)]
        if s.position == "kitchen":
            return 0
        return ah[(s.id, di)]

    def in_kit(s: StaffInput, di: int):
        if s.position == "kitchen":
            return work[(s.id, di)]
        if s.position == "hall":
            return 0
        return ak[(s.id, di)]

    def in_pos(s: StaffInput, di: int, pos: str):
        return in_hall(s, di) if pos == "hall" else in_kit(s, di)

    # 겸직 정직원의 미들은 주방일 때만
    for s in staff:
        if s.position == "both" and (s.id, 0) in sm:
            for di in range(n_days):
                m.Add(sm[(s.id, di)] <= ak[(s.id, di)])
        elif s.position == "hall" and (s.id, 0) in sm:
            for di in range(n_days):
                m.Add(sm[(s.id, di)] == 0)  # 홀은 미들 없음

    def _prod(a, b, name):
        y = m.NewBoolVar(name)
        m.Add(y <= a)
        m.Add(y <= b)
        m.Add(y >= a + b - 1)
        return y

    # --- 필요 인원 (포지션 x 슬롯) 커버 + 부족분 슬랙 (하한) ---
    shortage: dict[tuple[int, str, str], cp_model.IntVar] = {}
    for di, d in enumerate(days):
        wd = d.weekday()
        for pos in _POS_LABEL:
            for slot in _SLOTS:
                req = _req(inp, wd, pos, slot)
                terms = []
                for s in staff:
                    if s.is_part_time:
                        if pos == "hall" and slot == "mid":
                            continue                                 # 홀은 미들 없음
                        terms.append(in_pos(s, di, pos))            # 풀오마: 그 포지션 모든 슬롯 커버
                    elif s.is_close_only:
                        if slot == "close":
                            terms.append(in_pos(s, di, pos))        # 사장/점장: 마감만
                    else:
                        sv = {"open": so, "mid": sm, "close": sc}[slot].get((s.id, di))
                        if sv is None:
                            continue
                        if s.position == pos:
                            terms.append(sv)
                        elif s.position == "both":
                            terms.append(_prod(sv, in_pos(s, di, pos), f"y_{s.id}_{di}_{pos}_{slot}"))
                sh = m.NewIntVar(0, max(req, 1), f"sh_{di}_{pos}_{slot}")
                shortage[(di, pos, slot)] = sh
                if req > 0:
                    m.Add(sum(terms) + sh >= req)
                else:
                    m.Add(sh == 0)

    # --- 하루 총 출근 인원 목표 (소프트 하한, 기존 기능) ---
    #   포지션x슬롯 필요인원과 별개. 파트타임 하루 종일 근무가 슬롯 여러 개를
    #   혼자 채워도 실제 출근 "머릿수"는 이 값을 목표로 한다 (사장님·점장 포함).
    headcount_short: dict[int, cp_model.IntVar] = {}
    if inp.daily_headcount_target > 0:
        target_hc = inp.daily_headcount_target
        for di in range(n_days):
            total_work = sum(work[(s.id, di)] for s in staff)
            hs = m.NewIntVar(0, target_hc, f"hcshort_{di}")
            m.Add(total_work + hs >= target_hc)
            headcount_short[di] = hs

    # --- 하루 총 출근 인원 상한 ---
    #   그 날 "필요인원(포지션x슬롯) 총합"과 "하루 총 출근 인원 목표" 중 더 큰
    #   값을 그 날 배치 가능한 최대 인원으로 삼는다. 필요인원은 원래 하한(>=)만
    #   있어서, 다른 직원의 기본휴무 일수를 맞추려고 이미 다 채워진 날에 사람을
    #   더 욱여넣어도 막을 방법이 없었다 — 그게 실제 보고된 버그(필요인원보다
    #   많이 배치됨). 포지션x슬롯 단위가 아니라 하루 총원 단위로 상한을 두는 건
    #   "하루 총 출근 인원 목표"가 포지션 필요인원보다 일부러 더 큰 값으로
    #   설정될 수 있기 때문 (그 경우 특정 슬롯에 여유 인력을 배치하는 게 정상
    #   동작이라 슬롯 단위로 막으면 그 기능이 깨짐).
    daily_excess: dict[int, cp_model.IntVar] = {}
    for di, d in enumerate(days):
        wd = d.weekday()
        day_req_sum = sum(
            _req(inp, wd, pos, slot) for pos in _POS_LABEL for slot in _SLOTS
        )
        cap = max(day_req_sum, inp.daily_headcount_target)
        total_work = sum(work[(s.id, di)] for s in staff)
        de = m.NewIntVar(0, len(staff), f"dexcess_{di}")
        m.Add(total_work - de <= cap)
        daily_excess[di] = de

    # --- 관리 책임자 최소 1인 출근 (하드) ---
    mgr_group = [s for s in staff if s.in_manager_group]
    mgr_all_off_days: list[str] = []
    for di, d in enumerate(days):
        avail = [
            s
            for s in mgr_group
            if d not in inp.leave_dates.get(s.id, set())
            and d not in inp.blocked_dates.get(s.id, set())
        ]
        if not avail:
            if mgr_group:
                mgr_all_off_days.append(d.isoformat())
            continue
        m.Add(sum(work[(s.id, di)] for s in avail) >= 1)

    def workdays(sid: int):
        return sum(work[(sid, di)] for di in range(n_days))

    def leave_expr(s: StaffInput):
        """그 달 연차 일수 = 고정 날짜 연차 + 엔진이 고른 연차일."""
        fixed_lv = len(inp.leave_dates.get(s.id, set()) & day_set)
        return fixed_lv + sum(lv[(s.id, di)] for di in range(n_days) if (s.id, di) in lv)

    def off_expr(s: StaffInput):
        return n_days - leave_expr(s) - workdays(s.id)

    # --- 연차 개수 채우기: 못 채우면 슬랙(소프트, 필요인원 부족보다는 약함) ---
    leave_short: dict[int, cp_model.IntVar] = {}
    for s in staff:
        want = inp.leave_counts.get(s.id, 0)
        if want <= 0 or not any((s.id, di) in lv for di in range(n_days)):
            continue
        sh = m.NewIntVar(0, want, f"leaveshort_{s.id}")
        m.Add(sum(lv[(s.id, di)] for di in range(n_days) if (s.id, di) in lv) + sh == want)
        leave_short[s.id] = sh

    # --- 정직원/점장 기본휴무(D/O) 고정 (연차 제외) ---
    #   목표: 그 달 휴일수(D/O + 사전휴무) == 기본휴무 일수  (연차는 별개로 이미 빠짐)
    #   over_rest  = 기준보다 더 쉼 (= 근무일수 미달). 이건 절대 안 되게 최우선 벌점 +
    #                못 맞추면 명확한 경고 (마감 슬롯/사전휴무 등으로 못 채운 경우).
    #   under_rest = 기준보다 덜 쉼 (= 초과근무). 인원 부족 시 어쩔 수 없이 허용 + 경고.
    over_rest: dict[int, cp_model.IntVar] = {}
    under_rest: dict[int, cp_model.IntVar] = {}
    blk_over_target: set[int] = set()  # 사전휴무가 기본휴무보다 많은 직원
    for s in staff:
        if s.min_days_off <= 0:
            continue
        lvx = leave_expr(s)
        bk = len(inp.blocked_dates.get(s.id, set()) & day_set)
        target = s.min_days_off
        if bk > target:
            blk_over_target.add(s.id)
        need_work = n_days - lvx - target  # 기본휴무를 정확히 쓰면 이만큼 근무
        oe = off_expr(s)                   # = n_days - lv - workdays  (그 달 비근무·비연차 일수)

        over = m.NewIntVar(0, n_days, f"overrest_{s.id}")
        under = m.NewIntVar(0, n_days, f"underrest_{s.id}")
        m.Add(workdays(s.id) + over >= need_work)  # 근무일수 하한 (소프트, 최우선 벌점)
        m.Add(under >= target - oe)                # 초과근무 정도
        over_rest[s.id] = over
        under_rest[s.id] = under

    # --- 정직원·점장 휴무일수 공정성 (주말+공휴일 기준, 하드에 준함) ---
    #   대상: role in (staff, manager) 이면서 파트타임이 아니고 min_days_off > 0
    #   인 사람 (= 기본휴무 목표가 있는 사람. 사장님·파트타임은 애초에 비교 기준이 없어 제외).
    #   전원 똑같이 나누는 게 아니라, 그 달 "주말(토/일) + 등록된 공휴일"에서 각자
    #   MIN_WEEKEND_HOLIDAY_OFF일 이상 ~ MAX_WEEKEND_HOLIDAY_OFF일 이하로 쉬도록
    #   상·하한을 보장한다 (한 사람만 계속 주말·공휴일에 나오거나, 반대로 한 사람만
    #   계속 그쪽으로 휴무가 몰리는 것 둘 다 막는 게 목적이지, 정확히 균등 분배하는
    #   게 목적이 아님). 그 사람이 쉰 날 수 = 그 기간 일수 - 그 기간에 일한 날 수.
    #   D/O·연차·사전휴무 모두 work==0 으로 표현되므로 work 변수만 보면 셋을 합친
    #   총 휴무일수가 그대로 나온다. 최소/최대는 거의 하드로, 권장치(3일)는 그보다
    #   훨씬 약한 소프트 선호로 둬서 여유가 있으면 3일 쪽으로 당기되, 다른 우선순위
    #   높은 규칙과 부딪히면 쉽게 양보한다.
    #   최소/최대 보장은 아래 "사장님 주말 회피"보다 우선순위가 높다
    #   (W_OFFDAY_FAIR > W_OWNWKND) — 필요하면 사장님을 주말에 투입해서라도 맞춘다.
    #   권장치(3일) 선호는 그보다 약해서 사장님 주말 회피에 밀린다.
    MIN_WEEKEND_HOLIDAY_OFF = 2
    TARGET_WEEKEND_HOLIDAY_OFF = 3
    MAX_WEEKEND_HOLIDAY_OFF = 4
    weekend_holiday_idx = [
        di for di, d in enumerate(days) if d.weekday() >= 5 or d in inp.holiday_dates
    ]
    offday_fair_group = [s for s in staff if s.in_offday_fair_group]
    offday_min_short: dict[int, cp_model.IntVar] = {}
    offday_max_over: dict[int, cp_model.IntVar] = {}
    offday_target_dev: dict[int, cp_model.IntVar] = {}
    if weekend_holiday_idx and offday_fair_group:
        n_wh = len(weekend_holiday_idx)
        wh_min = min(MIN_WEEKEND_HOLIDAY_OFF, n_wh)  # 그 달 풀 자체가 더 작으면 그만큼만
        wh_max = min(MAX_WEEKEND_HOLIDAY_OFF, n_wh)
        wh_target = min(TARGET_WEEKEND_HOLIDAY_OFF, n_wh)
        for s in offday_fair_group:
            wh_off_expr = n_wh - sum(work[(s.id, di)] for di in weekend_holiday_idx)
            short = m.NewIntVar(0, wh_min, f"offday_min_short_{s.id}")
            m.Add(wh_off_expr + short >= wh_min)
            offday_min_short[s.id] = short

            over = m.NewIntVar(0, n_wh, f"offday_max_over_{s.id}")
            m.Add(wh_off_expr - over <= wh_max)
            offday_max_over[s.id] = over

            dev = m.NewIntVar(0, n_wh, f"offday_target_dev_{s.id}")
            m.Add(wh_off_expr - dev <= wh_target)
            m.Add(wh_off_expr + dev >= wh_target)
            offday_target_dev[s.id] = dev

    # --- 사장님 주말 회피 (소프트) + 2명 이상이면 휴일 균등 ---
    owners = [s for s in staff if s.is_owner]
    weekend_idx = [di for di, d in enumerate(days) if d.weekday() >= 5]
    owner_weekend = sum(work[(o.id, di)] for o in owners for di in weekend_idx)

    # --- 겸직 사장님: 마감은 홀(FC) 우선. 주방(BC) 배정에 가벼운 벌점 ---
    #   (홀 인원이 이미 충분하거나 주방이 부족하면 그래도 주방으로 감 — 부족분 벌점이 훨씬 큼)
    owner_kitchen = sum(
        ak[(o.id, di)]
        for o in owners
        if o.position == "both"
        for di in range(n_days)
    )
    owner_spread = None
    if len(owners) >= 2:
        omx = m.NewIntVar(0, n_days, "own_off_max")
        omn = m.NewIntVar(0, n_days, "own_off_min")
        for s in owners:
            m.Add(omx >= off_expr(s))
            m.Add(omn <= off_expr(s))
        owner_spread = m.NewIntVar(0, n_days, "own_off_spread")
        m.Add(owner_spread == omx - omn)

    # --- 공정성: 일반 정직원끼리 오픈/마감 횟수 균등 (포지션 그룹별로) ---
    #   홀 전담은 미들이 없어 O/C 가 많을 수밖에 없으므로, 같은 포지션끼리만 비교한다.
    fair = [s for s in staff if s.is_regular]
    fair_groups: dict[str, list[StaffInput]] = {}
    for s in fair:
        fair_groups.setdefault(s.position, []).append(s)
    fair_terms = []
    for gi, (_pos, members) in enumerate(fair_groups.items()):
        if len(members) < 2:
            continue
        for kind, slot in (("o", so), ("c", sc)):
            mx = m.NewIntVar(0, n_days, f"fair_{gi}_{kind}_max")
            mn = m.NewIntVar(0, n_days, f"fair_{gi}_{kind}_min")
            for s in members:
                cnt = sum(slot[(s.id, di)] for di in range(n_days))
                m.Add(mx >= cnt)
                m.Add(mn <= cnt)
            fair_terms.append(mx - mn)
    shift_fair = sum(fair_terms) if fair_terms else None

    # --- 주방 로테이션 선호도 (소프트) ---
    #   rotation_slot(open/mid/close) 이 있는 직원은 그 슬롯에 우선 배정한다.
    #   so/sm/sc 가 있는 직원(정직원 — 사장·점장·파트타임은 슬롯 구분이 없어 제외)에만
    #   적용. 그날 연차/사전휴무 등으로 못 나오면 work 자체가 0이라 벌점도 0 —
    #   "그날만 다른 사람이 채우고 로테이션 자체는 안 깨진다"는 요구사항이 자연히 성립.
    rotation_dev_terms = []
    for s in staff:
        if not s.rotation_slot or (s.id, 0) not in so:
            continue
        pref_var = {"open": so, "mid": sm, "close": sc}[s.rotation_slot]
        for di in range(n_days):
            rotation_dev_terms.append(work[(s.id, di)] - pref_var[(s.id, di)])
    rotation_dev = sum(rotation_dev_terms) if rotation_dev_terms else None

    # --- 마감 백업 선호도 (소프트) ---
    #   점장이 쉬는 날, close_backup=True 인 직원을 주방 마감에 우선 배정한다.
    #   점장이 정확히 1명일 때만 활성화 (0명/2명 이상이면 "쉬는 날" 의미가 불명확).
    managers = [s for s in staff if s.is_manager]
    backup_staff = [s for s in staff if s.close_backup and (s.id, 0) in sc]
    close_backup_terms = []
    if len(managers) == 1 and backup_staff:
        mgr = managers[0]
        for di in range(n_days):
            mgr_off = 1 - work[(mgr.id, di)]
            for b in backup_staff:
                not_close = 1 - sc[(b.id, di)]
                busy_not_close = _prod(work[(b.id, di)], not_close, f"backupnc_{b.id}_{di}")
                miss = _prod(mgr_off, busy_not_close, f"backupmiss_{b.id}_{di}")
                close_backup_terms.append(miss)
    close_backup_dev = sum(close_backup_terms) if close_backup_terms else None

    # --- 근무 몰림 완화 ---
    peak = m.NewIntVar(0, n_days, "peak")
    for s in staff:
        m.Add(workdays(s.id) <= peak)

    # --- 6일 이상 연속 근무 회피 (소프트) ---
    #   6일 연속 창(window) 마다 벌점. 7일 연속이면 2개 창이 걸려 더 큰 벌점 → 길수록 강하게 회피.
    #   달 경계는 고려하지 않음 (그 달 안에서만 계산).
    MAX_STREAK = 5
    streak_viol: list[cp_model.IntVar] = []
    for s in staff:
        for a in range(n_days - MAX_STREAK):
            win = [work[(s.id, di)] for di in range(a, a + MAX_STREAK + 1)]
            v = m.NewIntVar(0, 1, f"streak_{s.id}_{a}")
            m.Add(v >= sum(win) - MAX_STREAK)
            streak_viol.append(v)

    # === 목표 (스펙 5 우선순위) ===
    # CP-SAT 속도를 위해 계단식이 아닌 '적당히 벌어진' 가중치를 쓴다.
    # 위→아래: 근무일수 미달(기본휴무 위반) > 인원부족 = 인원초과 > 초과근무 >
    #          정직원·점장 휴무공정성(주말+공휴일 최소/최대) > 6일연속 > 사장주말 >
    #          휴무공정성 권장치(3일) = 주방로테이션 선호 = 마감백업 선호 >
    #          사장휴일균등 > 공정성 > 근무몰림 > 총근무
    # 인원초과가 인원부족과 동급인 이유: 필요인원은 "정해진 인원" — 부족도
    # 안 되고 초과도 안 됨. 다만 직원 총 근무 가능일이 필요인원 총합보다 많아
    # (여유 인력) 기본휴무를 정확히 맞추려면 초과 배치가 불가피한 극히 드문
    # 경우엔, 그보다 우선순위가 높은 기본휴무 준수를 위해 초과를 허용하고
    # 경고로 알린다.
    # 휴무공정성이 사장주말보다 우선순위가 높은 이유: 정직원·점장 각자 주말·
    # 공휴일에 최소 며칠은 쉬도록 보장하는 게, 사장님의 주말 근무를 피하는
    # 것보다 우선이라고 요청받음 — 필요하면 사장님이 주말에 들어간다.
    # "권장 3일"(W_OFFDAY_TARGET)은 최소/최대 보장보다는 약하지만, 겸직사장
    # 마감포지션(60)·사장휴일균등(80)·공정성(25)·근무몰림(4) 같은 그 아래
    # 소프트 규칙들보다는 확실히 강하게 잡는다 — 안 그러면 그 규칙들이 만드는
    # 미세한 유불리 때문에 D/O 배치가 3일이 아니라 4일 쪽으로 흘러가 버린다
    # (연차·사전휴무처럼 하드로 고정된 휴무는 이 가중치로도 못 건드리므로,
    # 그게 4일을 만들면 그대로 허용된다 — 엔진이 스스로 만드는 D/O만 3일에 맞춘다).
    # 다만 사장님 주말 회피(250)보다는 낮게 둬서 그 규칙 우선순위는 유지한다.
    W_OVERREST = 500_000   # 기준보다 더 쉬는 것(근무일수 미달) = 사실상 하드
    W_SHORT = 100_000
    W_DAILY_EXCESS = 100_000  # 하루 총원 상한 초과 (부족과 동급 우선순위)
    W_HEADCOUNT = 100_000  # 하루 총 출근 인원 목표 미달 (필요인원과 동급 우선순위)
    W_LEAVE_SHORT = 20_000  # 요청한 연차 개수를 못 채움 — 필요인원 부족(100,000)보다 약해서
                            # 연차 때문에 인원이 모자라느니 연차를 덜 넣는다
    W_UNDERREST = 4_000    # 초과근무 (인원 부족 시 허용)
    W_OFFDAY_FAIR = 2_000  # 정직원·점장 휴무공정성(주말+공휴일 최소/최대) 위반 (하드에 준함)
    W_STREAK = 1_000       # 6일 이상 연속 근무 (불가피하면 허용)
    W_OWNWKND = 250
    W_OFFDAY_TARGET = 200  # 휴무공정성 권장치(3일) 쪽으로 당기는 선호 (사장주말보다만 약함)
    W_ROTATION_PREF = 150  # 주방 로테이션 기본 포지션 우선 배정 (소프트)
    W_CLOSE_BACKUP = 150   # 점장 결근 시 마감 백업 우선 배정 (소프트)
    W_OWNSPREAD = 80
    W_OWNKITCHEN = 60      # 겸직 사장 마감을 주방(BC)에 넣는 것 (홀 우선)
    W_FAIR = 25
    W_PEAK = 4

    obj = (
        W_OVERREST * sum(over_rest.values())
        + W_SHORT * sum(shortage.values())
        + W_DAILY_EXCESS * sum(daily_excess.values())
        + W_HEADCOUNT * sum(headcount_short.values())
        + W_UNDERREST * sum(under_rest.values())
        + W_STREAK * sum(streak_viol)
        + W_OWNWKND * owner_weekend
        + W_OWNKITCHEN * owner_kitchen
        + W_PEAK * peak
        + sum(work.values())
    )
    if offday_min_short:
        obj += W_OFFDAY_FAIR * sum(offday_min_short.values())
    if offday_max_over:
        obj += W_OFFDAY_FAIR * sum(offday_max_over.values())
    if offday_target_dev:
        obj += W_OFFDAY_TARGET * sum(offday_target_dev.values())
    if leave_short:
        obj += W_LEAVE_SHORT * sum(leave_short.values())
    if lv:
        # 연차일을 랜덤하게 흩뿌리기 위한 아주 작은 가중치 (다른 규칙엔 영향 없는 동점 깨기)
        obj += sum(rng.randint(0, 3) * v for v in lv.values())
    if rotation_dev is not None:
        obj += W_ROTATION_PREF * rotation_dev
    if close_backup_dev is not None:
        obj += W_CLOSE_BACKUP * close_backup_dev
    if owner_spread is not None:
        obj += W_OWNSPREAD * owner_spread
    if shift_fair is not None:
        obj += W_FAIR * shift_fair
    m.Minimize(obj)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers = 8
    status = solver.Solve(m)
    result.solve_seconds = round(solver.WallTime(), 3)

    for d in mgr_all_off_days:
        result.warnings.append(
            SolveWarning(d, "관리책임자", 1, 0, f"{d}: 사장님·점장이 모두 연차 — 관리 책임자 출근을 못 넣었습니다")
        )

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result.warnings.append(
            SolveWarning("", "", 0, 0, "해를 찾지 못했습니다. 설정을 확인해주세요.")
        )
        result.feasible = False
        return result

    def pos_of(s: StaffInput, di: int) -> str:
        if s.position == "hall":
            return "hall"
        if s.position == "kitchen":
            return "kitchen"
        return "hall" if solver.Value(ah[(s.id, di)]) == 1 else "kitchen"

    # --- 결과 + 요약 ---
    for s in staff:
        off = inp.leave_dates.get(s.id, set())
        blk = inp.blocked_dates.get(s.id, set())
        summ = {
            "open": 0, "mid": 0, "close": 0, "full": 0,
            "hall": 0, "kitchen": 0,
            "off": 0, "leave": 0, "blocked": 0, "work": 0,
        }
        for di, d in enumerate(days):
            key = d.isoformat()
            if d in off:
                code = CODE_LEAVE
                summ["leave"] += 1
            elif d in blk:
                code = CODE_BLOCKED
                summ["blocked"] += 1
            elif (s.id, di) in lv and solver.Value(lv[(s.id, di)]) == 1:
                code = CODE_LEAVE
                summ["leave"] += 1
                result.leave_placed[s.id] = result.leave_placed.get(s.id, 0) + 1
            elif solver.Value(work[(s.id, di)]) == 1:
                p = pos_of(s, di)
                if s.is_part_time:
                    code = CODE_FULL
                    summ["full"] += 1
                elif s.is_close_only:
                    code = CODE_FC if p == "hall" else CODE_BC
                    summ["close"] += 1
                elif solver.Value(so[(s.id, di)]):
                    code = CODE_FO if p == "hall" else CODE_BO
                    summ["open"] += 1
                elif solver.Value(sc[(s.id, di)]):
                    code = CODE_FC if p == "hall" else CODE_BC
                    summ["close"] += 1
                else:
                    code = CODE_BM  # 미들은 주방만
                    summ["mid"] += 1
                summ["work"] += 1
                summ[p] += 1
            else:
                code = CODE_OFF
                summ["off"] += 1
            result.entries[s.id][key] = code
        result.shift_summary[s.id] = summ

    # --- 경고: 필요 인원 부족 ---
    total_short = 0
    for di, d in enumerate(days):
        wd = d.weekday()
        for pos in _POS_LABEL:
            for slot in _SLOTS:
                v = solver.Value(shortage[(di, pos, slot)])
                if v > 0:
                    req = _req(inp, wd, pos, slot)
                    total_short += v
                    result.warnings.append(
                        SolveWarning(
                            d.isoformat(),
                            f"{_POS_LABEL[pos]}·{_SLOT_LABEL[slot]}",
                            req,
                            req - v,
                            f"{d.isoformat()} {_POS_LABEL[pos]} {_SLOT_LABEL[slot]}: {req}명 필요, {req - v}명 (−{v})",
                        )
                    )

    # --- 경고: 하루 총 출근 인원 목표 미달 ---
    total_hc_short = 0
    for di, d in enumerate(days):
        hs = headcount_short.get(di)
        if hs is None:
            continue
        v = solver.Value(hs)
        if v > 0:
            total_hc_short += v
            filled = inp.daily_headcount_target - v
            result.warnings.append(
                SolveWarning(
                    d.isoformat(),
                    "총원",
                    inp.daily_headcount_target,
                    filled,
                    f"{d.isoformat()}: 총 출근 인원 {inp.daily_headcount_target}명 목표인데 "
                    f"{filled}명만 배치 (−{v}) · 근무 가능한 사람이 부족합니다",
                )
            )

    # --- 경고: 하루 총 출근 인원 상한 초과 ---
    total_daily_excess = 0
    for di, d in enumerate(days):
        wd = d.weekday()
        v = solver.Value(daily_excess[di])
        if v > 0:
            day_req_sum = sum(
                _req(inp, wd, pos, slot) for pos in _POS_LABEL for slot in _SLOTS
            )
            cap = max(day_req_sum, inp.daily_headcount_target)
            total_daily_excess += v
            result.warnings.append(
                SolveWarning(
                    d.isoformat(),
                    "총원",
                    cap,
                    cap + v,
                    f"{d.isoformat()}: 필요인원 {cap}명인데 {cap + v}명 배치 (+{v}) · "
                    f"다른 직원 근무일수를 맞추느라 초과 배치됐습니다",
                )
            )

    # --- 경고: 정직원/점장 근무일수(기본휴무) 미달 = 기준보다 더 쉼 ---
    name_by_id = {s.id: s.name for s in staff}
    target_by_id = {s.id: s.min_days_off for s in staff}
    over_gap = 0
    for sid, over in over_rest.items():
        g = solver.Value(over)
        if g > 0:
            over_gap += g
            want = target_by_id[sid]
            got_work = solver.Value(workdays(sid))
            reason = (
                "사전 휴무가 기본휴무보다 많습니다"
                if sid in blk_over_target
                else "마감 슬롯이 부족해 근무를 다 못 넣었습니다"
            )
            result.warnings.append(
                SolveWarning(
                    "", "근무일수", want, want + g,
                    f"{name_by_id[sid]}: 기본휴무 {want}일 기준이면 근무 {n_days - want}일 정도여야 "
                    f"하는데 {got_work}일만 배치 (−{g}) · {reason}",
                )
            )

    # --- 경고: 초과근무 (기준보다 덜 쉼) ---
    under_gap = 0
    for sid, und in under_rest.items():
        g = solver.Value(und)
        if g > 0:
            under_gap += g
            want = target_by_id[sid]
            result.warnings.append(
                SolveWarning(
                    "", "초과근무", want, want - g,
                    f"{name_by_id[sid]}: 기본휴무 {want}일 목표인데 {want - g}일만 쉼 (+{g}일 초과근무) · 인원이 부족합니다",
                )
            )

    # --- 경고: 요청한 연차 개수를 다 못 넣은 경우 ---
    for sid, sh in leave_short.items():
        g = solver.Value(sh)
        if g > 0:
            want = inp.leave_counts[sid]
            result.warnings.append(
                SolveWarning(
                    "", "연차", want, want - g,
                    f"{name_by_id[sid]}: 연차 {want}개 중 {want - g}개만 배치 — "
                    f"인원이 부족해지는 날에는 연차를 넣지 않습니다",
                )
            )

    # --- 경고: 정직원·점장 주말·공휴일 최소 휴무일수를 못 채운 경우 ---
    offday_min_gap = 0
    for sid, short in offday_min_short.items():
        g = solver.Value(short)
        if g > 0:
            offday_min_gap += g
            wh_off_v = MIN_WEEKEND_HOLIDAY_OFF - g
            result.warnings.append(
                SolveWarning(
                    "", "휴무공정성", MIN_WEEKEND_HOLIDAY_OFF, wh_off_v,
                    f"{name_by_id[sid]}: 주말·공휴일 최소 휴무 {MIN_WEEKEND_HOLIDAY_OFF}일 "
                    f"목표인데 {wh_off_v}일만 쉼 (−{g}) · 인원이 부족합니다",
                )
            )

    # --- 경고: 정직원·점장 주말·공휴일 최대 휴무일수를 초과한 경우 ---
    offday_max_gap = 0
    for sid, over in offday_max_over.items():
        g = solver.Value(over)
        if g > 0:
            offday_max_gap += g
            wh_off_v = MAX_WEEKEND_HOLIDAY_OFF + g
            result.warnings.append(
                SolveWarning(
                    "", "휴무공정성", MAX_WEEKEND_HOLIDAY_OFF, wh_off_v,
                    f"{name_by_id[sid]}: 주말·공휴일 최대 휴무 {MAX_WEEKEND_HOLIDAY_OFF}일 "
                    f"기준인데 {wh_off_v}일 쉼 (+{g}) · 다른 인원 근무일수를 맞추느라 몰렸습니다",
                )
            )

    # --- 경고: 6일 이상 연속 근무 (불가피하게 발생한 경우) ---
    for s in staff:
        run = 0
        best = 0
        run_start = ""
        best_range = ("", "")
        for di, d in enumerate(days):
            if result.entries[s.id][d.isoformat()] in WORK_CODES:
                if run == 0:
                    run_start = d.isoformat()
                run += 1
                if run > best:
                    best = run
                    best_range = (run_start, d.isoformat())
            else:
                run = 0
        if best >= MAX_STREAK + 1:
            result.warnings.append(
                SolveWarning(
                    "", "연속근무", MAX_STREAK, best,
                    f"{s.name}: {best}일 연속 근무 ({best_range[0]}~{best_range[1]}) · 인원이 부족해 불가피",
                )
            )

    result.feasible = (
        total_short == 0
        and total_daily_excess == 0
        and total_hc_short == 0
        and over_gap == 0
        and under_gap == 0
        and not mgr_all_off_days
    )
    return result
