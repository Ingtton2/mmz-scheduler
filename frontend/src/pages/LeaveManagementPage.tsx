// 사전휴무 관리 화면 (스펙 3) — "사전휴무 승인" + "연차 사용 현황" 탭 통합.
//  - 사전휴무 목록은 월별 + 직원별로 필터해서 볼 수 있다.
//  - 사전휴무 승인: 사전 휴무 신청(날짜 기반)을 승인/반려. 연차는 날짜로 신청하지 않는다 —
//    사장님이 부여하고, 자동배치 실행 때 직원별 사용 개수를 정하면 날짜는 자동배치가 고른다.
//  - 연차 사용 현황: 부여/사용/잔여 연차 조회 + 연차 추가.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createDayOffRequest,
  deleteDayOffRequest,
  listDayOffRequests,
  updateDayOffRequest,
  MAX_PER_MONTH,
  type DayOffRequest,
} from "../api/dayoff";
import { listStaff, type Staff } from "../api/staff";
import { LABEL } from "../labels";
import ConfirmDialog from "../components/ConfirmDialog";
import MonthFilterBar from "../components/MonthFilterBar";
import Pagination, { paginate } from "../components/Pagination";
import { rangeOverlapsMonth, todayYm } from "../utils/month";
import { fmtRange } from "../utils/format";
import LeaveUsageTab from "./LeaveUsageTab";

const todayStr = () => new Date().toISOString().slice(0, 10);

type Status = "requested" | "confirmed" | "rejected";

type Row = {
  id: number;
  staff_id: number;
  staff_name: string;
  start_date: string;
  end_date: string;
  days: number;
  applied_at: string;
  status: Status;
  note: string | null;
  reject_reason: string | null;
};

// 대기 -> 승인 -> 반려 -> 대기 순으로 클릭할 때마다 전환.
const NEXT_STATUS: Record<Status, Status> = {
  requested: "confirmed",
  confirmed: "rejected",
  rejected: "requested",
};

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

export default function LeaveManagementPage() {
  const [tab, setTab] = useState<"approval" | "usage">("approval");
  const [staff, setStaff] = useState<Staff[]>([]);
  const [dayoffRequests, setDayoffRequests] = useState<DayOffRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);
  // 반려로 넘길 때 사유를 받는 중인 신청 (사유는 필수)
  const [rejecting, setRejecting] = useState<{ id: number; reason: string } | null>(null);
  const [monthFilter, setMonthFilter] = useState<string | null>(todayYm());
  const [staffFilter, setStaffFilter] = useState("");
  const [page, setPage] = useState(1);

  const [form, setForm] = useState({
    staff_id: "",
    start_date: todayStr(),
    end_date: todayStr(),
    note: "",
  });

  const selectedStaff = staff.find((s) => s.id === Number(form.staff_id));
  const isPartTime = selectedStaff?.employment_type === "part_time";

  const rows: Row[] = dayoffRequests
    .map(
      (r): Row => ({
        id: r.id,
        staff_id: r.staff_id,
        staff_name: r.staff_name,
        start_date: r.start_date,
        end_date: r.end_date,
        days: r.days,
        applied_at: r.applied_at,
        status: r.status,
        note: r.note,
        reject_reason: r.reject_reason,
      }),
    )
    .sort((a, b) => a.start_date.localeCompare(b.start_date));

  const staffRows = staffFilter
    ? rows.filter((r) => r.staff_id === Number(staffFilter))
    : rows;

  const visibleRows =
    monthFilter === null
      ? staffRows
      : staffRows.filter((r) => rangeOverlapsMonth(r.start_date, r.end_date, monthFilter));
  const pagedRows = paginate(visibleRows, page);

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
      const [s, dr] = await Promise.all([listStaff(), listDayOffRequests()]);
      setStaff(s);
      setDayoffRequests(dr);
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

  // 사전휴무 선택 시: 이 직원이 시작일이 속한 달에 이미 신청한 일수
  const targetYm = form.start_date.slice(0, 7);
  const usedThisMonth =
    form.staff_id
      ? dayoffRequests
          .filter((r) => r.staff_id === Number(form.staff_id))
          .reduce((sum, r) => sum + daysInMonth(r.start_date, r.end_date, targetYm), 0)
      : 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.staff_id) {
      setError("직원을 선택해 주세요.");
      return;
    }
    if (isPartTime) {
      setError("파트타임은 신청 대상이 아닙니다.");
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

  async function toggleStatus(r: Row) {
    const next = NEXT_STATUS[r.status];
    if (next === "rejected") {
      // 반려는 사유를 적어야 넘어간다 — 사유 입력칸을 먼저 연다.
      setRejecting({ id: r.id, reason: "" });
      return;
    }
    try {
      await updateDayOffRequest(r.id, { status: next });
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function confirmReject() {
    if (!rejecting || !rejecting.reason.trim()) return;
    try {
      await updateDayOffRequest(rejecting.id, {
        status: "rejected",
        reject_reason: rejecting.reason.trim(),
      });
      setRejecting(null);
      setError("");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function handleDelete(r: Row) {
    try {
      await deleteDayOffRequest(r.id);
      setPendingDelete(null);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const field = "rounded border border-gray-300 px-3 py-2 text-sm";
  const hasStaff = staff.length > 0;
  const rowKey = (r: Row) => String(r.id);

  return (
    <div>
      <div className="mb-4 flex items-center gap-2 text-sm text-gray-500">
        <Link to="/admin" className="hover:underline">
          관리자 홈
        </Link>
        <span>/</span>
        <span className="text-gray-800">사전휴무 관리</span>
      </div>

      <h1 className="mb-4 text-xl font-bold">사전휴무 관리</h1>

      {/* --- 탭 --- */}
      <div className="mb-4 flex gap-1 border-b">
        {(
          [
            ["approval", "사전휴무 승인"],
            ["usage", "연차 사용 현황"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={
              "-mb-px border-b-2 px-4 py-2 text-sm font-medium " +
              (tab === key
                ? "border-primary text-primary"
                : "border-transparent text-gray-500 hover:text-gray-700")
            }
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "approval" ? (
        <>
          <p className="mb-4 text-sm text-gray-500">
            사전휴무 신청을 승인/반려할 수 있으며, 등록된 날짜는 자동배치 때 그 직원을 그 날
            빼고 시작합니다. 연차는 날짜로 신청하지 않고, 근무표 관리에서 자동배치를 돌릴 때
            직원별 사용 개수를 정해요 (부여·조회는 “연차 사용 현황” 탭).
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

            {isPartTime ? (
              <p className="rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">
                파트타임은 신청 대상이 아닙니다.
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
                    placeholder="예: 병원 예약, 가족 행사"
                  />
                </label>

                <button
                  type="submit"
                  disabled={saving || !hasStaff}
                  className="rounded bg-primary hover:bg-primary-dark px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  {saving ? "저장 중…" : "신청 추가"}
                </button>

                {form.staff_id && (
                  <span
                    className={
                      "text-xs " +
                      (usedThisMonth >= MAX_PER_MONTH ? "text-red-600" : "text-gray-400")
                    }
                  >
                    {targetYm} 신청 {usedThisMonth}/{MAX_PER_MONTH}일
                  </span>
                )}
              </>
            )}
          </form>

          {error && (
            <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
          )}

          {/* --- 신청 목록 --- */}
          <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border bg-white px-3 py-2">
            <label htmlFor="staff-filter" className="text-sm font-medium">
              직원별 보기
            </label>
            <select
              id="staff-filter"
              className={field}
              value={staffFilter}
              onChange={(e) => {
                setStaffFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">전체 직원</option>
              {staff.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
            <span className="text-xs text-gray-400">
              “전체 보기”를 함께 누르면 그 직원의 전체 이력을 볼 수 있어요.
            </span>
          </div>
          <MonthFilterBar
            month={monthFilter}
            onChange={(ym) => {
              setMonthFilter(ym);
              setPage(1);
            }}
            total={staffRows.length}
            shown={visibleRows.length}
          />
          <div className="overflow-x-auto rounded-lg border bg-white">
            <table className="w-full text-sm">
              <thead className="border-b bg-gray-50 text-left text-gray-500">
                <tr>
                  <th className="px-3 py-2">기간</th>
                  <th className="px-3 py-2">직원</th>
                  <th className="px-3 py-2">신청일</th>
                  <th className="px-3 py-2">상태</th>
                  <th className="px-3 py-2">메모</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-center text-gray-400">
                      불러오는 중…
                    </td>
                  </tr>
                ) : visibleRows.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-center text-gray-400">
                      {staffRows.length === 0
                        ? staffFilter
                          ? "이 직원의 사전휴무 신청이 없습니다."
                          : "아직 등록된 사전휴무 신청이 없습니다."
                        : "이 달에는 신청 내역이 없습니다."}
                    </td>
                  </tr>
                ) : (
                  pagedRows.map((r) => (
                    <tr key={rowKey(r)} className="border-b last:border-0">
                      <td className="px-3 py-2 font-medium whitespace-nowrap">
                        {fmtRange(r.start_date, r.end_date, r.days)}
                      </td>
                      <td className="px-3 py-2">{r.staff_name}</td>
                      <td className="px-3 py-2 whitespace-nowrap text-gray-500">
                        {r.applied_at}
                      </td>
                      <td className="px-3 py-2">
                        <button
                          onClick={() => toggleStatus(r)}
                          className={
                            "rounded-full px-2 py-0.5 text-xs font-semibold " +
                            (r.status === "confirmed"
                              ? "bg-mint text-mint-ink"
                              : r.status === "rejected"
                                ? "bg-warn text-warn-ink"
                                : "bg-amber-100 text-amber-800")
                          }
                          title="눌러서 상태 전환"
                        >
                          {LABEL.leaveStatus[r.status] ?? r.status}
                        </button>
                        {r.status === "rejected" && r.reject_reason && (
                          <div className="mt-1 max-w-[14rem] text-xs text-gray-500">
                            사유: {r.reject_reason}
                          </div>
                        )}
                        {rejecting?.id === r.id && (
                          <div className="mt-2 flex flex-wrap items-center gap-1">
                            <input
                              autoFocus
                              value={rejecting.reason}
                              onChange={(e) => setRejecting({ id: r.id, reason: e.target.value })}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") confirmReject();
                                if (e.key === "Escape") setRejecting(null);
                              }}
                              placeholder="반려 사유 (필수)"
                              className="w-44 rounded border border-gray-300 px-2 py-1 text-xs"
                            />
                            <button
                              onClick={confirmReject}
                              disabled={!rejecting.reason.trim()}
                              className="rounded bg-red-600 px-2 py-1 text-xs text-white disabled:opacity-40"
                            >
                              반려 확정
                            </button>
                            <button
                              onClick={() => setRejecting(null)}
                              className="text-xs text-gray-500 hover:underline"
                            >
                              취소
                            </button>
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2 text-gray-600">{r.note ?? ""}</td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">
                        <button
                          onClick={() => setPendingDelete(rowKey(r))}
                          className="text-xs text-red-600 hover:underline"
                        >
                          삭제
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <Pagination page={page} total={visibleRows.length} onChange={setPage} />

          <p className="mt-3 text-xs text-gray-400">
            총 {staffRows.length}건 · “상태” 칸을 누르면 대기 → 승인 → 반려 순으로
            전환되고, 반려로 바꿀 땐 사유를 적어야 해요. “신청일”은 실제 쉬는 날짜와 다른, 신청서를 낸 날입니다.
          </p>
        </>
      ) : (
        <LeaveUsageTab />
      )}

      {pendingDelete !== null && (
        <ConfirmDialog
          title="삭제하시겠습니까?"
          message={(() => {
            const r = rows.find((x) => rowKey(x) === pendingDelete);
            return r ? `${r.staff_name} · ${fmtRange(r.start_date, r.end_date, r.days)}` : undefined;
          })()}
          onConfirm={() => {
            const r = rows.find((x) => rowKey(x) === pendingDelete);
            if (r) handleDelete(r);
            else setPendingDelete(null);
          }}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </div>
  );
}
