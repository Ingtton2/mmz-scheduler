// 사전 휴무 신청 관리 화면 (스펙 3.1).
//  - 연차와 별개: 그날 배치 제외되지만 총 근무일수는 유지 (자동배치가 다른 날로 채움), 연차 차감 없음
//  - 직원 1명당 한 달 최대 20일. 초과하면 서버가 거부.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  MAX_PER_MONTH,
  createDayOffRequest,
  deleteDayOffRequest,
  listDayOffRequests,
  type DayOffRequest,
} from "../api/dayoff";
import { listStaff, type Staff } from "../api/staff";
import { fmtRange } from "./LeavePage";
import MonthFilterBar from "../components/MonthFilterBar";
import { rangeOverlapsMonth, todayYm } from "../utils/month";

const todayStr = () => new Date().toISOString().slice(0, 10);
const ym = (d: string) => d.slice(0, 7); // "2026-10"

// 기간 안에서 특정 달(ym)에 걸치는 일수
function daysInMonth(start: string, end: string, targetYm: string): number {
  let n = 0;
  const d = new Date(start + "T00:00:00");
  const last = new Date(end + "T00:00:00");
  while (d <= last) {
    if (d.toISOString().slice(0, 7) === targetYm) n++;
    d.setDate(d.getDate() + 1);
  }
  return n;
}

export default function DayOffPage() {
  const [staff, setStaff] = useState<Staff[]>([]);
  const [requests, setRequests] = useState<DayOffRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<number | null>(null);
  const [monthFilter, setMonthFilter] = useState<string | null>(todayYm());

  const [form, setForm] = useState({
    staff_id: "",
    start_date: todayStr(),
    end_date: todayStr(),
    note: "",
  });

  const selectedStaff = staff.find((s) => s.id === Number(form.staff_id));
  const isPartTime = selectedStaff?.employment_type === "part_time";

  const visibleRequests =
    monthFilter === null
      ? requests
      : requests.filter((r) => rangeOverlapsMonth(r.start_date, r.end_date, monthFilter));

  function setStart(v: string) {
    setForm((f) => ({
      ...f,
      start_date: v,
      end_date: f.end_date < v ? v : f.end_date,
    }));
  }

  async function refresh() {
    setLoading(true);
    try {
      const [s, r] = await Promise.all([listStaff(), listDayOffRequests()]);
      setStaff(s);
      setRequests(r);
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

  // 선택한 직원이 시작일이 속한 달에 이미 신청한 일수
  const targetYm = ym(form.start_date);
  const usedThisMonth = form.staff_id
    ? requests
        .filter((r) => r.staff_id === Number(form.staff_id))
        .reduce(
          (sum, r) => sum + daysInMonth(r.start_date, r.end_date, targetYm),
          0,
        )
    : 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.staff_id) {
      setError("직원을 선택해 주세요.");
      return;
    }
    if (isPartTime) {
      setError("파트타임은 사전 휴무 신청 대상이 아닙니다.");
      return;
    }
    setSaving(true);
    try {
      await createDayOffRequest({
        staff_id: Number(form.staff_id),
        start_date: form.start_date,
        end_date: form.end_date,
        note: form.note.trim() || null,
      });
      setForm({ ...form, note: "" });
      setError("");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteDayOffRequest(id);
      setPendingDelete(null);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const field = "rounded border border-gray-300 px-3 py-2 text-sm";
  const hasStaff = staff.length > 0;

  return (
    <div>
      <div className="mb-4 flex items-center gap-2 text-sm text-gray-500">
        <Link to="/admin" className="hover:underline">
          관리자 홈
        </Link>
        <span>/</span>
        <span className="text-gray-800">사전 휴무 신청</span>
      </div>

      <h1 className="mb-1 text-xl font-bold">사전 휴무 신청</h1>
      <p className="mb-4 text-sm text-gray-500">
        스케줄 생성 전에 “이 날짜는 근무 불가”를 미리 신청합니다.{" "}
        <b>연차와 다릅니다</b> — 그날 배치는 빠지지만 총 근무일수는 그대로이고
        (자동배치가 다른 날로 옮겨 채움), 연차는 차감되지 않습니다. 직원 1명당 한
        달 최대 {MAX_PER_MONTH}일.
      </p>

      {!hasStaff && !loading && (
        <p className="mb-4 rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">
          먼저{" "}
          <Link to="/admin/staff" className="underline">
            직원 등록
          </Link>{" "}
          화면에서 직원을 추가해 주세요.
        </p>
      )}

      <form
        onSubmit={handleSubmit}
        className="mb-6 flex flex-wrap items-end gap-3 rounded-lg border bg-white p-4"
      >
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">직원</span>
          <select
            className={field}
            value={form.staff_id}
            onChange={(e) => setForm({ ...form, staff_id: e.target.value })}
            disabled={!hasStaff}
          >
            <option value="">선택하세요</option>
            {staff.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>

        {isPartTime ? (
          <p className="rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">
            파트타임은 사전 휴무 신청 대상이 아닙니다.
          </p>
        ) : (
          <>
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">시작일</span>
              <input
                type="date"
                className={field}
                value={form.start_date}
                onChange={(e) => setStart(e.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">종료일</span>
              <input
                type="date"
                className={field}
                min={form.start_date}
                value={form.end_date}
                onChange={(e) => setForm({ ...form, end_date: e.target.value })}
              />
            </label>

            <label className="flex flex-1 flex-col gap-1 text-sm">
              <span className="font-medium">메모 (선택)</span>
              <input
                className={field}
                value={form.note}
                onChange={(e) => setForm({ ...form, note: e.target.value })}
                placeholder="예: 가족 행사, 개인 사정"
              />
            </label>

            <button
              type="submit"
              disabled={saving || !hasStaff}
              className="rounded bg-primary hover:bg-primary-dark px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {saving ? "저장 중…" : "사전 휴무 추가"}
            </button>

            {form.staff_id && (
              <span
                className={
                  "text-xs " +
                  (usedThisMonth >= MAX_PER_MONTH
                    ? "text-red-600"
                    : "text-gray-400")
                }
              >
                {targetYm} 신청 {usedThisMonth}/{MAX_PER_MONTH}일
              </span>
            )}
          </>
        )}
      </form>

      {error && (
        <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <MonthFilterBar
        month={monthFilter}
        onChange={setMonthFilter}
        total={requests.length}
        shown={visibleRequests.length}
      />
      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="px-3 py-2">기간</th>
              <th className="px-3 py-2">직원</th>
              <th className="px-3 py-2">메모</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={4} className="px-3 py-6 text-center text-gray-400">
                  불러오는 중…
                </td>
              </tr>
            ) : visibleRequests.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-3 py-6 text-center text-gray-400">
                  {requests.length === 0
                    ? "아직 등록된 사전 휴무 신청이 없습니다."
                    : "이 달에는 신청 내역이 없습니다."}
                </td>
              </tr>
            ) : (
              visibleRequests.map((r) => (
                <tr key={r.id} className="border-b last:border-0">
                  <td className="px-3 py-2 font-medium whitespace-nowrap">
                    {fmtRange(r.start_date, r.end_date, r.days)}
                  </td>
                  <td className="px-3 py-2">{r.staff_name}</td>
                  <td className="px-3 py-2 text-gray-600">{r.note ?? ""}</td>
                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    {pendingDelete === r.id ? (
                      <>
                        <span className="text-xs text-gray-500">삭제할까요?</span>
                        <button
                          onClick={() => handleDelete(r.id)}
                          className="ml-2 rounded bg-red-600 px-2 py-0.5 text-xs text-white"
                        >
                          삭제
                        </button>
                        <button
                          onClick={() => setPendingDelete(null)}
                          className="ml-1 text-xs text-gray-500 hover:underline"
                        >
                          취소
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => setPendingDelete(r.id)}
                        className="text-xs text-red-600 hover:underline"
                      >
                        삭제
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-xs text-gray-400">
        총 {requests.length}건 · 자동배치에서 이 날짜는 “사휴”로 표시되며 그
        직원은 배치되지 않습니다. 데이터는 day_off_request 표에 저장됩니다.
      </p>
    </div>
  );
}
