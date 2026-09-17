// 필요 인원 설정 화면 (스펙 4) — 포지션 x 시간대(오픈/미들/마감).
//  - "기본값 (매일 공통)" 에 값 넣고 "모든 요일에 적용" -> 7요일 일괄 세팅
//  - 표에서 특정 요일만 다르게 조정
//  - 홀은 미들 시간대 없음 (오픈/마감만)
//  - "저장" 을 눌러야 서버(staffing_requirement 표)에 반영
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createHoliday,
  deleteHoliday,
  getHolidays,
  type HolidayItem,
} from "../api/holiday";
import {
  getDailyHeadcountTarget,
  getStaffingRequirements,
  putDailyHeadcountTarget,
  putStaffingRequirements,
  type StaffingItem,
} from "../api/staffing";
import { WEEKDAYS } from "../labels";

// 격자의 한 셀 키
const COLS = [
  { key: "hall_open", label: "홀 오픈", position: "hall", slot: "open" },
  { key: "hall_close", label: "홀 마감", position: "hall", slot: "close" },
  { key: "kit_open", label: "주방 오픈", position: "kitchen", slot: "open" },
  { key: "kit_mid", label: "주방 미들", position: "kitchen", slot: "mid" },
  { key: "kit_close", label: "주방 마감", position: "kitchen", slot: "close" },
] as const;

type ColKey = (typeof COLS)[number]["key"];
type Row = Record<ColKey, string>;
type Grid = Record<number, Row>;

const DEFAULT_BASE: Row = {
  hall_open: "1",
  hall_close: "1",
  kit_open: "1",
  kit_mid: "1",
  kit_close: "2",
};

const emptyGrid = (): Grid => {
  const g: Grid = {};
  for (const w of WEEKDAYS) g[w.value] = { ...DEFAULT_BASE };
  return g;
};

const num = (s: string) => {
  const n = parseInt(s, 10);
  return Number.isFinite(n) && n >= 0 ? n : 0;
};

export default function StaffingPage() {
  const [grid, setGrid] = useState<Grid>(emptyGrid());
  const [base, setBase] = useState<Row>({ ...DEFAULT_BASE });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [savedMsg, setSavedMsg] = useState("");

  const [headcountTarget, setHeadcountTarget] = useState("0");
  const [savingHeadcount, setSavingHeadcount] = useState(false);
  const [headcountSavedMsg, setHeadcountSavedMsg] = useState("");

  const [holidays, setHolidays] = useState<HolidayItem[]>([]);
  const [newHolidayDate, setNewHolidayDate] = useState("");
  const [newHolidayName, setNewHolidayName] = useState("");
  const [savingHoliday, setSavingHoliday] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const [items, hc, hol] = await Promise.all([
        getStaffingRequirements(),
        getDailyHeadcountTarget(),
        getHolidays(),
      ]);
      setHolidays(hol);
      const g = emptyGrid();
      // 서버 값으로 덮어쓰기 (없는 칸은 0)
      for (const w of WEEKDAYS)
        for (const c of COLS) g[w.value][c.key] = "0";
      for (const it of items) {
        const col = COLS.find(
          (c) => c.position === it.position && c.slot === it.time_slot,
        );
        if (col && g[it.weekday]) g[it.weekday][col.key] = String(it.min_headcount);
      }
      setGrid(g);
      setHeadcountTarget(String(hc.daily_headcount_target));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function saveHeadcountTarget() {
    setSavingHeadcount(true);
    try {
      const v = await putDailyHeadcountTarget(num(headcountTarget));
      setHeadcountTarget(String(v.daily_headcount_target));
      setHeadcountSavedMsg("저장되었습니다.");
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingHeadcount(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function addHoliday() {
    if (!newHolidayDate || !newHolidayName.trim()) return;
    setSavingHoliday(true);
    try {
      await createHoliday(newHolidayDate, newHolidayName.trim());
      setNewHolidayDate("");
      setNewHolidayName("");
      setHolidays(await getHolidays());
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingHoliday(false);
    }
  }

  async function removeHoliday(id: number) {
    try {
      await deleteHoliday(id);
      setHolidays((hs) => hs.filter((h) => h.id !== id));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function applyBase() {
    const g: Grid = {};
    for (const w of WEEKDAYS) g[w.value] = { ...base };
    setGrid(g);
    setSavedMsg("");
  }

  function setCell(weekday: number, key: ColKey, value: string) {
    setGrid({ ...grid, [weekday]: { ...grid[weekday], [key]: value } });
    setSavedMsg("");
  }

  async function save() {
    setSaving(true);
    try {
      const items: StaffingItem[] = [];
      for (const w of WEEKDAYS)
        for (const c of COLS)
          items.push({
            weekday: w.value,
            position: c.position,
            time_slot: c.slot,
            min_headcount: num(grid[w.value][c.key]),
          });
      await putStaffingRequirements(items);
      setError("");
      setSavedMsg("저장되었습니다.");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  const inp = "w-14 rounded border border-gray-300 px-1.5 py-1 text-right text-sm";

  return (
    <div>
      <div className="mb-4 flex items-center gap-2 text-sm text-gray-500">
        <Link to="/admin" className="hover:underline">
          관리자 홈
        </Link>
        <span>/</span>
        <span className="text-gray-800">필요 인원 설정</span>
      </div>

      <h1 className="mb-1 text-xl font-bold">필요 인원 설정</h1>
      <p className="mb-4 text-sm text-gray-500">
        포지션(홀/주방) × 시간대(오픈/미들/마감)별로 최소 인원을 정합니다.
        자동배치가 이 인원을 채우려 시도하고, 못 채우면 경고로 알려줍니다.
        (홀은 미들 시간대 없음)
      </p>

      {/* 하루 총 출근 인원 목표 */}
      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border bg-white p-4">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">하루 총 출근 인원 목표</span>
          <span className="text-xs text-gray-500">
            요일 무관 동일 값 (사장님·점장 포함). 파트타임이 하루 종일 근무해
            자리를 여러 개 혼자 채워도, 실제 출근 인원 수는 이 값에 맞춥니다.
            0이면 이 규칙을 끕니다.
          </span>
          <input
            type="number"
            min={0}
            className={inp}
            value={headcountTarget}
            onChange={(e) => {
              setHeadcountTarget(e.target.value);
              setHeadcountSavedMsg("");
            }}
          />
        </label>
        <button
          onClick={saveHeadcountTarget}
          disabled={savingHeadcount || loading}
          className="rounded bg-primary hover:bg-primary-dark px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {savingHeadcount ? "저장 중…" : "저장"}
        </button>
        {headcountSavedMsg && (
          <span className="text-sm text-green-700">{headcountSavedMsg}</span>
        )}
      </div>

      {/* 공휴일 관리 */}
      <div className="mb-4 rounded-lg border bg-white p-4">
        <div className="mb-1 text-sm font-medium">공휴일 관리</div>
        <p className="mb-3 text-xs text-gray-500">
          한국 공휴일(대체공휴일 포함)은 매년 날짜가 달라 자동 계산하지 않습니다.
          날짜를 직접 등록하면 스케줄표에 표시됩니다. 자동배치 로직에는 영향을
          주지 않습니다.
        </p>
        <div className="mb-3 flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs text-gray-600">날짜</span>
            <input
              type="date"
              className="rounded border border-gray-300 px-2 py-1 text-sm"
              value={newHolidayDate}
              onChange={(e) => setNewHolidayDate(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs text-gray-600">이름</span>
            <input
              type="text"
              placeholder="예: 추석"
              className="w-32 rounded border border-gray-300 px-2 py-1 text-sm"
              value={newHolidayName}
              onChange={(e) => setNewHolidayName(e.target.value)}
            />
          </label>
          <button
            onClick={addHoliday}
            disabled={savingHoliday || !newHolidayDate || !newHolidayName.trim()}
            className="rounded bg-primary hover:bg-primary-dark px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {savingHoliday ? "등록 중…" : "등록"}
          </button>
        </div>
        {holidays.length === 0 ? (
          <p className="text-xs text-gray-400">등록된 공휴일이 없습니다.</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {holidays.map((h) => (
              <li
                key={h.id}
                className="flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs text-amber-800"
              >
                <span>
                  {h.date} · {h.name}
                </span>
                <button
                  onClick={() => removeHoliday(h.id)}
                  className="text-amber-600 hover:text-amber-900"
                  aria-label={`${h.date} ${h.name} 삭제`}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 기본값 일괄 적용 */}
      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border bg-white p-4">
        <span className="text-sm font-medium">기본값 (매일 공통)</span>
        {COLS.map((c) => (
          <label key={c.key} className="flex flex-col gap-1 text-sm">
            <span className="text-xs text-gray-600">{c.label}</span>
            <input
              type="number"
              min={0}
              className={inp}
              value={base[c.key]}
              onChange={(e) => setBase({ ...base, [c.key]: e.target.value })}
            />
          </label>
        ))}
        <button
          onClick={applyBase}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
        >
          모든 요일에 적용
        </button>
      </div>

      {/* 요일별 표 */}
      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-50 text-gray-500">
            <tr>
              <th className="px-3 py-2 text-left">요일</th>
              {COLS.map((c) => (
                <th key={c.key} className="px-3 py-2 text-right whitespace-nowrap">
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-gray-400">
                  불러오는 중…
                </td>
              </tr>
            ) : (
              WEEKDAYS.map((w) => (
                <tr
                  key={w.value}
                  className={
                    "border-b last:border-0 " +
                    (w.value >= 5 ? "bg-amber-50/40" : "")
                  }
                >
                  <td className="px-3 py-2 font-medium">{w.label}요일</td>
                  {COLS.map((c) => (
                    <td key={c.key} className="px-3 py-2 text-right">
                      <input
                        type="number"
                        min={0}
                        className={inp}
                        value={grid[w.value][c.key]}
                        onChange={(e) => setCell(w.value, c.key, e.target.value)}
                      />
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {error && (
        <p className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {savedMsg && (
        <p className="mt-4 rounded bg-green-50 px-3 py-2 text-sm text-green-700">
          {savedMsg}
        </p>
      )}

      <button
        onClick={save}
        disabled={saving || loading}
        className="mt-4 rounded bg-primary hover:bg-primary-dark px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {saving ? "저장 중…" : "저장"}
      </button>

      <p className="mt-3 text-xs text-gray-400">
        토·일요일 줄은 옅게 표시됩니다. 파트타임은 "풀오마"로 하루 전체를 커버하며
        이 슬롯 계산에 함께 반영됩니다.
      </p>
    </div>
  );
}
