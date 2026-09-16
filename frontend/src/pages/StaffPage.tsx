// 사장님용 "직원 등록/관리" 화면 (스펙 6.1, 3).
//  - 정적 정보만 관리: 이름/역할/포지션/고용형태/근무 가능 요일/입사일
//  - 월 최소 휴무일수(기본휴무)는 연차와 별개 값이라 여기 그대로 둠
//  - 연차(부여/사용/잔여) 관리는 "연차 관리" 메뉴에서 한다.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createStaff,
  deleteStaff,
  listStaff,
  updateLeaveBalance,
  updateStaff,
  type LeaveBalanceInput,
  type Staff,
} from "../api/staff";
import { EMPLOYMENT_TYPES, LABEL, POSITIONS, ROLES, WEEKDAYS } from "../labels";

const fmtWeekdays = (days: number[], fixed: boolean) => {
  if (days.length === 7) return "매일";
  const labels = WEEKDAYS.filter((w) => days.includes(w.value)).map((w) => w.label);
  return labels.join("·") + (fixed ? " (고정)" : "");
};

// 서버 API는 아직 연차 숫자 4개를 한 번에 받는다(다음 단계에서 데이터 모델 정리 예정).
// 이 페이지는 base_off_days 만 수정하고, 나머지는 기존 값을 그대로 실어 보낸다(덮어쓰기 방지).
type LeaveForm = LeaveBalanceInput;
const EMPTY_LEAVE: LeaveForm = {
  base_off_days: 8, // 월 최소 휴무 기본값
  granted: 0,
  used: 0,
};

const EMPTY_FORM = {
  name: "",
  role: "staff",
  position: "hall",
  employment_type: "full_time",
  work_weekdays: [0, 1, 2, 3, 4, 5, 6] as number[],
  fixed_schedule: false,
  hire_date: "",
  leave: { ...EMPTY_LEAVE },
};

export default function StaffPage() {
  const [staff, setStaff] = useState<Staff[]>([]);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [pendingDelete, setPendingDelete] = useState<number | null>(null);

  // 기존 직원 클릭 -> 등록 폼에 정보 채워서 수정 모드로 전환 (삭제 후 재등록 금지).
  const [editingStaffId, setEditingStaffId] = useState<number | null>(null);

  const isOwner = form.role === "owner";
  // 월 최소 휴무는 정직원 + 점장(정직원)만
  const showBaseOff =
    (form.role === "staff" || form.role === "manager") &&
    form.employment_type === "full_time";

  async function refresh() {
    setLoading(true);
    try {
      setStaff(await listStaff());
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

  function toggleWeekday(v: number) {
    const has = form.work_weekdays.includes(v);
    const next = has
      ? form.work_weekdays.filter((d) => d !== v)
      : [...form.work_weekdays, v].sort((a, b) => a - b);
    setForm({ ...form, work_weekdays: next });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) return setError("이름을 입력해 주세요.");
    if (form.work_weekdays.length === 0)
      return setError("근무 가능 요일을 하나 이상 선택해 주세요.");
    setSaving(true);
    try {
      if (editingStaffId != null) {
        await updateStaff(editingStaffId, {
          name: form.name.trim(),
          role: form.role,
          position: form.position,
          employment_type: isOwner ? null : form.employment_type,
          work_weekdays: form.work_weekdays,
          fixed_schedule: form.fixed_schedule,
          hire_date: form.hire_date || null,
        });
        if (showBaseOff) {
          await updateLeaveBalance(editingStaffId, form.leave);
        }
        setEditingStaffId(null);
      } else {
        await createStaff({
          name: form.name.trim(),
          role: form.role,
          position: form.position,
          employment_type: isOwner ? null : form.employment_type,
          work_weekdays: form.work_weekdays,
          fixed_schedule: form.fixed_schedule,
          hire_date: form.hire_date || null,
          leave: form.leave,
        });
      }
      setForm({ ...EMPTY_FORM, work_weekdays: [0, 1, 2, 3, 4, 5, 6], leave: { ...EMPTY_LEAVE } });
      setError("");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  function startEditStaff(s: Staff) {
    setEditingStaffId(s.id);
    setError("");
    setForm({
      name: s.name,
      role: s.role,
      position: s.position,
      employment_type: s.employment_type ?? "full_time",
      work_weekdays: s.work_weekdays,
      fixed_schedule: s.fixed_schedule,
      hire_date: s.hire_date ?? "",
      // 기존 연차 숫자는 그대로 보존해서 실어 보낸다 (base_off_days만 화면에서 수정).
      leave: s.leave
        ? {
            base_off_days: s.leave.base_off_days,
            granted: s.leave.granted,
            used: s.leave.used,
          }
        : { ...EMPTY_LEAVE },
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEditStaff() {
    setEditingStaffId(null);
    setForm({ ...EMPTY_FORM, work_weekdays: [0, 1, 2, 3, 4, 5, 6], leave: { ...EMPTY_LEAVE } });
    setError("");
  }

  async function handleDelete(id: number) {
    try {
      await deleteStaff(id);
      setPendingDelete(null);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function toggleFixed(s: Staff) {
    try {
      await updateStaff(s.id, { fixed_schedule: !s.fixed_schedule });
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const field = "rounded border border-gray-300 px-3 py-2 text-sm";
  const numField = "w-28 rounded border border-gray-300 px-2 py-1 text-sm";

  return (
    <div>
      <div className="mb-4 flex items-center gap-2 text-sm text-gray-500">
        <Link to="/admin" className="hover:underline">
          관리자 홈
        </Link>
        <span>/</span>
        <span className="text-gray-800">직원 등록/관리</span>
      </div>

      <h1 className="mb-4 text-xl font-bold">직원 등록/관리</h1>

      {/* --- 등록/수정 폼 --- */}
      <form
        onSubmit={handleSubmit}
        className={
          "mb-6 rounded-lg border bg-white p-4" +
          (editingStaffId != null ? " ring-2 ring-amber-400" : "")
        }
      >
        <div className="mb-3 flex items-center justify-between">
          <span className="text-sm font-semibold text-gray-700">
            {editingStaffId != null ? "직원 정보 수정" : "새 직원 등록"}
          </span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">이름</span>
            <input
              className={field}
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="예: 김홀서"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">역할</span>
            <select
              className={field}
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
            >
              {ROLES.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">포지션</span>
            <select
              className={field}
              value={form.position}
              onChange={(e) => setForm({ ...form, position: e.target.value })}
            >
              {POSITIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            {isOwner && (
              <span className="text-xs text-gray-400">
                홀만 가능한 사장님은 “홀 전담”, 홀·주방 다 되는 사장님은 “겸직”.
              </span>
            )}
          </label>

          {!isOwner && (
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">고용형태</span>
              <select
                className={field}
                value={form.employment_type}
                onChange={(e) =>
                  setForm({ ...form, employment_type: e.target.value })
                }
              >
                {EMPLOYMENT_TYPES.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          )}

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">입사일</span>
            <input
              type="date"
              className={field}
              value={form.hire_date}
              onChange={(e) => setForm({ ...form, hire_date: e.target.value })}
            />
          </label>
        </div>

        {/* --- 근무 가능 요일 --- */}
        <fieldset className="mt-4 rounded border border-gray-200 p-3">
          <legend className="px-1 text-sm font-medium text-gray-600">
            근무 가능 요일
          </legend>
          <div className="flex flex-wrap items-center gap-1.5">
            {WEEKDAYS.map((w) => {
              const on = form.work_weekdays.includes(w.value);
              return (
                <button
                  type="button"
                  key={w.value}
                  onClick={() => toggleWeekday(w.value)}
                  className={
                    "h-8 w-8 rounded text-sm " +
                    (on
                      ? "bg-primary hover:bg-primary-dark text-white"
                      : "border border-gray-300 text-gray-500")
                  }
                >
                  {w.label}
                </button>
              );
            })}
            <label className="ml-3 flex items-center gap-1.5 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={form.fixed_schedule}
                onChange={(e) =>
                  setForm({ ...form, fixed_schedule: e.target.checked })
                }
              />
              선택한 요일에 항상 배치 (파트타임 고정 근무)
            </label>
          </div>
          <p className="mt-2 text-xs text-gray-400">
            정직원은 보통 매일(전체 선택). 파트타임은 나오는 요일만 선택하세요.
          </p>
        </fieldset>

        {/* --- 월 최소 휴무 (정직원만, 연차와 별개) --- */}
        {showBaseOff ? (
          <fieldset className="mt-4 rounded border border-gray-200 p-3">
            <legend className="px-1 text-sm font-medium text-gray-600">
              월 최소 휴무
            </legend>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-gray-600">기본휴무 (월 고정, 연차 제외)</span>
              <input
                type="number"
                step={1}
                min={0}
                className={numField}
                value={form.leave.base_off_days}
                onChange={(e) =>
                  setForm({
                    ...form,
                    leave: {
                      ...form.leave,
                      base_off_days: Math.trunc(Number(e.target.value) || 0),
                    },
                  })
                }
              />
            </label>
            <p className="mt-2 text-xs text-gray-400">
              자동배치가 한 달에 맞추려는 최소 휴무일 수입니다(기본 8일). 연차는
              여기 포함되지 않고 “연차 관리” 메뉴에서 따로 관리합니다.
            </p>
          </fieldset>
        ) : (
          <p className="mt-3 text-xs text-gray-400">
            {isOwner ? "사장님" : "파트타임"}은 월 최소 휴무를 관리하지 않습니다.
            {form.role === "manager" &&
              " (점장은 정직원이면 관리합니다 — 고용형태를 정직원으로 두세요)"}
          </p>
        )}

        <div className="mt-4 flex gap-2">
          <button
            type="submit"
            disabled={saving}
            className="rounded bg-primary hover:bg-primary-dark px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? "저장 중…" : editingStaffId != null ? "수정 저장" : "직원 추가"}
          </button>
          {editingStaffId != null && (
            <button
              type="button"
              onClick={cancelEditStaff}
              disabled={saving}
              className="rounded border px-4 py-2 text-sm disabled:opacity-50"
            >
              취소
            </button>
          )}
        </div>
      </form>

      {error && (
        <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {/* --- 목록 --- */}
      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="px-3 py-2">이름</th>
              <th className="px-3 py-2">역할</th>
              <th className="px-3 py-2">포지션</th>
              <th className="px-3 py-2">고용형태</th>
              <th className="px-3 py-2">근무 요일</th>
              <th className="px-3 py-2">입사일</th>
              <th className="px-3 py-2 text-right">월휴일</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-gray-400">
                  불러오는 중…
                </td>
              </tr>
            ) : staff.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-gray-400">
                  아직 등록된 직원이 없습니다.
                </td>
              </tr>
            ) : (
              staff.map((s) => (
                <StaffRow
                  key={s.id}
                  s={s}
                  onToggleFixed={() => toggleFixed(s)}
                  confirmingDelete={pendingDelete === s.id}
                  onAskDelete={() => setPendingDelete(s.id)}
                  onCancelDelete={() => setPendingDelete(null)}
                  onConfirmDelete={() => handleDelete(s.id)}
                  editingInfo={editingStaffId === s.id}
                  onStartEditInfo={() => startEditStaff(s)}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-xs text-gray-400">
        총 {staff.length}명 · “월휴일”은 자동배치가 맞추려는 한 달 휴무일(D/O)
        수이며(기본 8일, 정직원만), 연차는 여기에 포함되지 않습니다. 사장님이
        2명 이상이면 서로 휴일 수를 최대한 같게 맞춥니다. 연차 부여/사용 현황은
        “연차 관리” 메뉴에서 확인하세요.
      </p>
    </div>
  );
}

function StaffRow({
  s,
  onToggleFixed,
  confirmingDelete,
  onAskDelete,
  onCancelDelete,
  onConfirmDelete,
  editingInfo,
  onStartEditInfo,
}: {
  s: Staff;
  onToggleFixed: () => void;
  confirmingDelete: boolean;
  onAskDelete: () => void;
  onCancelDelete: () => void;
  onConfirmDelete: () => void;
  editingInfo: boolean;
  onStartEditInfo: () => void;
}) {
  const restricted = s.work_weekdays.length < 7;
  return (
    <tr className={"border-b last:border-0" + (editingInfo ? " bg-amber-50" : "")}>
      <td className="px-3 py-2 font-medium">
        <button
          type="button"
          onClick={onStartEditInfo}
          className="hover:underline"
          title="눌러서 이 직원 정보 수정"
        >
          {s.name}
        </button>
      </td>
      <td className="px-3 py-2">{LABEL.role[s.role] ?? s.role}</td>
      <td className="px-3 py-2">{LABEL.position[s.position] ?? s.position}</td>
      <td className="px-3 py-2">
        {s.employment_type
          ? (LABEL.employment[s.employment_type] ?? s.employment_type)
          : "—"}
      </td>
      <td className="px-3 py-2">
        <span className={restricted ? "text-gray-800" : "text-gray-400"}>
          {fmtWeekdays(s.work_weekdays, s.fixed_schedule)}
        </span>
        {restricted && (
          <button
            onClick={onToggleFixed}
            className="ml-2 text-[11px] text-gray-400 hover:underline"
            title="고정 근무 켜기/끄기"
          >
            {s.fixed_schedule ? "고정 해제" : "고정 설정"}
          </button>
        )}
      </td>
      <td className="px-3 py-2">
        {s.hire_date ?? <span className="text-gray-300">—</span>}
      </td>

      <td className="px-3 py-2 text-right">
        {s.leave ? s.leave.base_off_days : <span className="text-gray-300">—</span>}
      </td>

      <td className="px-3 py-2 text-right whitespace-nowrap">
        {confirmingDelete ? (
          <>
            <span className="text-xs text-gray-500">삭제할까요?</span>
            <button
              onClick={onConfirmDelete}
              className="ml-2 rounded bg-red-600 px-2 py-0.5 text-xs text-white"
            >
              삭제
            </button>
            <button
              onClick={onCancelDelete}
              className="ml-1 text-xs text-gray-500 hover:underline"
            >
              취소
            </button>
          </>
        ) : (
          <>
            <button
              onClick={onStartEditInfo}
              className="text-xs text-gray-600 hover:underline"
            >
              정보 수정
            </button>
            <button
              onClick={onAskDelete}
              className="ml-2 text-xs text-red-600 hover:underline"
            >
              삭제
            </button>
          </>
        )}
      </td>
    </tr>
  );
}
