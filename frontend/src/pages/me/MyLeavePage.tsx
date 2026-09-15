// 내 연차 신청 (스펙 9-4, 9-5). 다음 달 스케줄분만, 이번 달 20일까지.
import { useEffect, useState } from "react";
import {
  createMyLeave,
  getMe,
  listMyLeave,
  type MeInfo,
  type MyLeaveRequest,
} from "../../api/me";
import { MeApiError } from "../../api/meClient";
import { LABEL } from "../../labels";
import { fmtRange } from "../LeavePage";
import { selfServiceTargetYm, selfServiceWindowOpen, ymLabel } from "../../utils/month";
import MeNav from "./MeNav";

const todayStr = () => new Date().toISOString().slice(0, 10);

export default function MyLeavePage() {
  const [me, setMe] = useState<MeInfo | null>(null);
  const [requests, setRequests] = useState<MyLeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const windowOpen = selfServiceWindowOpen();
  const targetYm = selfServiceTargetYm();

  const [form, setForm] = useState({
    start_date: todayStr(),
    end_date: todayStr(),
    note: "",
  });

  function setStart(v: string) {
    setForm((f) => ({ ...f, start_date: v, end_date: f.end_date < v ? v : f.end_date }));
  }

  async function refresh() {
    setLoading(true);
    try {
      const [meInfo, r] = await Promise.all([getMe(), listMyLeave()]);
      setMe(meInfo);
      setRequests(r);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "불러오기 실패");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const isPartTime = me?.employment_type === "part_time";
  const canSubmit = windowOpen && !isPartTime;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await createMyLeave(form.start_date, form.end_date, form.note.trim() || undefined);
      setForm({ ...form, note: "" });
      setError("");
      await refresh();
    } catch (err) {
      setError(err instanceof MeApiError ? err.message : "신청에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  const field = "rounded border border-gray-300 px-3 py-2 text-sm";

  return (
    <div>
      <MeNav current="연차 신청" />
      <h1 className="mb-1 text-xl font-bold">연차 신청</h1>
      <p className="mb-4 text-sm text-gray-500">
        신청한 날짜는 다음 자동배치 때 근무에서 빠집니다 (연차 잔여일수 차감).
      </p>

      {isPartTime ? (
        <p className="mb-4 rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">
          파트타임은 연차 신청 대상이 아닙니다.
        </p>
      ) : !windowOpen ? (
        <p className="mb-4 rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">
          이번 달 셀프 신청 기간(20일)이 지났습니다. 사장님께 말씀해서 관리자
          화면에서 등록해 주세요.
        </p>
      ) : (
        <p className="mb-4 rounded bg-gray-50 px-3 py-2 text-xs text-gray-500">
          지금 신청 가능: <b>{ymLabel(targetYm)}</b> 스케줄분 (이번 달 20일까지)
        </p>
      )}

      {canSubmit && (
        <form
          onSubmit={onSubmit}
          className="mb-6 flex flex-wrap items-end gap-3 rounded-lg border bg-white p-4"
        >
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
            disabled={saving}
            className="rounded-lg bg-[#B08968] hover:bg-[#997555] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? "신청 중…" : "연차 신청"}
          </button>
        </form>
      )}

      {error && (
        <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="px-3 py-2">기간</th>
              <th className="px-3 py-2">상태</th>
              <th className="px-3 py-2">메모</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={3} className="px-3 py-6 text-center text-gray-400">
                  불러오는 중…
                </td>
              </tr>
            ) : requests.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-3 py-6 text-center text-gray-400">
                  아직 신청한 연차가 없습니다.
                </td>
              </tr>
            ) : (
              requests.map((r) => (
                <tr key={r.id} className="border-b last:border-0">
                  <td className="px-3 py-2 font-medium whitespace-nowrap">
                    {fmtRange(r.start_date, r.end_date, r.days)}
                  </td>
                  <td className="px-3 py-2">
                    <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                      {LABEL.leaveStatus[r.status] ?? r.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-gray-600">{r.note ?? ""}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
