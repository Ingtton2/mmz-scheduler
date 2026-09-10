// 연차 신청 관리 화면 (스펙 3).
// 지금은 직원이 직접 신청하는 대신 사장님이 대신 입력하는 방식.
// 여기서 등록한 연차 날짜는 나중에 자동배치에서 '최우선 고정'으로 쓰인다.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createLeaveRequest,
  deleteLeaveRequest,
  listLeaveRequests,
  updateLeaveRequest,
  type LeaveRequest,
} from "../api/leave";
import { listStaff, type Staff } from "../api/staff";
import { LABEL } from "../labels";

const todayStr = () => new Date().toISOString().slice(0, 10);

export function fmtRange(start: string, end: string, days: number): string {
  return start === end ? start : `${start} ~ ${end} (${days}일)`;
}

export default function LeavePage() {
  const [staff, setStaff] = useState<Staff[]>([]);
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<number | null>(null);

  const [form, setForm] = useState({
    staff_id: "",
    start_date: todayStr(),
    end_date: todayStr(),
    note: "",
  });

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
      const [s, r] = await Promise.all([listStaff(), listLeaveRequests()]);
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.staff_id) {
      setError("직원을 선택해 주세요.");
      return;
    }
    setSaving(true);
    try {
      await createLeaveRequest({
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

  async function toggleStatus(r: LeaveRequest) {
    try {
      await updateLeaveRequest(r.id, {
        status: r.status === "confirmed" ? "requested" : "confirmed",
      });
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteLeaveRequest(id);
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
        <span className="text-gray-800">연차 신청 관리</span>
      </div>

      <h1 className="mb-1 text-xl font-bold">연차 신청 관리</h1>
      <p className="mb-4 text-sm text-gray-500">
        직원이 원하는 연차 날짜를 사장님이 대신 등록합니다. 등록된 날짜는
        자동배치 때 그 직원을 그 날 빼고 시작합니다. (파트타임·사장님도 “그 날
        빼기” 용도로 쓸 수 있으며, 연차 잔여일수와는 무관합니다.)
      </p>

      {!hasStaff && !loading && (
        <p className="mb-4 rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">
          먼저 <Link to="/admin/staff" className="underline">직원 등록</Link> 화면에서
          직원을 추가해 주세요.
        </p>
      )}

      {/* --- 신청 폼 --- */}
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
            placeholder="예: 병원 예약, 가족 행사"
          />
        </label>

        <button
          type="submit"
          disabled={saving || !hasStaff}
          className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {saving ? "저장 중…" : "연차 신청 추가"}
        </button>
      </form>

      {error && (
        <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {/* --- 신청 목록 --- */}
      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="px-3 py-2">기간</th>
              <th className="px-3 py-2">직원</th>
              <th className="px-3 py-2">상태</th>
              <th className="px-3 py-2">메모</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-gray-400">
                  불러오는 중…
                </td>
              </tr>
            ) : requests.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-gray-400">
                  아직 등록된 연차 신청이 없습니다.
                </td>
              </tr>
            ) : (
              requests.map((r) => (
                <tr key={r.id} className="border-b last:border-0">
                  <td className="px-3 py-2 font-medium whitespace-nowrap">
                    {fmtRange(r.start_date, r.end_date, r.days)}
                  </td>
                  <td className="px-3 py-2">{r.staff_name}</td>
                  <td className="px-3 py-2">
                    <button
                      onClick={() => toggleStatus(r)}
                      className={
                        "rounded px-2 py-0.5 text-xs " +
                        (r.status === "confirmed"
                          ? "bg-green-100 text-green-800"
                          : "bg-gray-100 text-gray-600")
                      }
                      title="눌러서 상태 전환"
                    >
                      {LABEL.leaveStatus[r.status] ?? r.status}
                    </button>
                  </td>
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
        총 {requests.length}건 · “상태” 칸을 누르면 신청 ↔ 확정 이 전환됩니다.
        데이터는 leave_request 표에 저장됩니다.
      </p>
    </div>
  );
}
