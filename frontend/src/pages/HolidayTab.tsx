// "필요 인원 설정 > 공휴일 관리" 탭.
//  - 한국 공휴일(대체공휴일 포함)은 매년 날짜가 달라 자동 계산하지 않고, 관리자가 직접 등록/삭제.
//  - 등록한 날짜는 자동배치 화면(SchedulePage)의 스케줄표에 표시만 됨 (자동배치 로직엔 영향 없음).
import { useEffect, useState } from "react";
import {
  createHoliday,
  deleteHoliday,
  getHolidays,
  type HolidayItem,
} from "../api/holiday";

export default function HolidayTab() {
  const [holidays, setHolidays] = useState<HolidayItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [newDate, setNewDate] = useState("");
  const [newName, setNewName] = useState("");
  const [saving, setSaving] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      setHolidays(await getHolidays());
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function addHoliday() {
    if (!newDate || !newName.trim()) return;
    setSaving(true);
    try {
      await createHoliday(newDate, newName.trim());
      setNewDate("");
      setNewName("");
      setHolidays(await getHolidays());
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
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

  return (
    <>
      <p className="mb-4 text-sm text-gray-500">
        한국 공휴일(대체공휴일 포함)은 매년 날짜가 달라 자동 계산하지 않습니다.
        날짜를 직접 등록하면 자동배치 화면의 스케줄표에 표시됩니다. 자동배치
        로직에는 영향을 주지 않습니다.
      </p>

      <div className="mb-4 rounded-lg border bg-white p-4">
        <div className="mb-3 flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs text-gray-600">날짜</span>
            <input
              type="date"
              className="rounded border border-gray-300 px-2 py-1 text-sm"
              value={newDate}
              onChange={(e) => setNewDate(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs text-gray-600">이름</span>
            <input
              type="text"
              placeholder="예: 추석"
              className="w-32 rounded border border-gray-300 px-2 py-1 text-sm"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
          </label>
          <button
            onClick={addHoliday}
            disabled={saving || !newDate || !newName.trim()}
            className="rounded bg-primary hover:bg-primary-dark px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? "등록 중…" : "등록"}
          </button>
        </div>

        {error && (
          <p className="mb-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        {loading ? (
          <p className="text-xs text-gray-400">불러오는 중…</p>
        ) : holidays.length === 0 ? (
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
    </>
  );
}
