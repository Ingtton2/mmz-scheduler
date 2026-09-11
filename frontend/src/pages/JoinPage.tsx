// 직원 셀프서비스 가입 신청 (스펙 9). QR/링크로 접속, 로그인 없음.
// 기존 직원 목록에서 본인 선택 + 4자리 PIN 설정 -> 사장님 승인 대기.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAvailableForSignup, signup, type AvailableStaff } from "../api/me";
import { MeApiError } from "../api/meClient";
import { LABEL } from "../labels";

export default function JoinPage() {
  const [staff, setStaff] = useState<AvailableStaff[]>([]);
  const [staffId, setStaffId] = useState("");
  const [pin, setPin] = useState("");
  const [pin2, setPin2] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ status: string; message: string } | null>(null);

  useEffect(() => {
    listAvailableForSignup()
      .then(setStaff)
      .catch((e) => setError(e instanceof Error ? e.message : "불러오기 실패"))
      .finally(() => setLoading(false));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!staffId) return setError("본인 이름을 선택해 주세요.");
    if (pin.length !== 4 || !/^\d{4}$/.test(pin)) return setError("PIN은 숫자 4자리여야 합니다.");
    if (pin !== pin2) return setError("PIN이 서로 일치하지 않습니다.");
    setSaving(true);
    try {
      const res = await signup(Number(staffId), pin);
      setResult(res);
    } catch (err) {
      setError(err instanceof MeApiError ? err.message : "가입 신청에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  const field = "w-full rounded border border-gray-300 px-3 py-2 text-sm";

  if (result) {
    return (
      <div className="mx-auto mt-16 max-w-sm rounded-lg border bg-white p-6 text-center shadow-sm">
        <h1 className="mb-2 text-lg font-bold">가입 신청 완료</h1>
        <p className="mb-4 text-sm text-gray-600">{result.message}</p>
        <Link to="/staff-login" className="text-sm text-gray-900 underline">
          로그인 화면으로 이동
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto mt-16 max-w-sm rounded-lg border bg-white p-6 shadow-sm">
      <h1 className="mb-1 text-lg font-bold">직원 가입 신청</h1>
      <p className="mb-5 text-sm text-gray-500">
        본인 이름을 목록에서 선택하고, 앞으로 로그인에 쓸 4자리 PIN을 정해주세요.
      </p>
      <form onSubmit={onSubmit} className="space-y-3">
        <div>
          <label className="mb-1 block text-sm text-gray-600">본인 이름</label>
          <select
            className={field}
            value={staffId}
            onChange={(e) => setStaffId(e.target.value)}
            disabled={loading}
          >
            <option value="">
              {loading ? "불러오는 중…" : "선택하세요"}
            </option>
            {staff.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({LABEL.role[s.role] ?? s.role} · {LABEL.position[s.position] ?? s.position})
              </option>
            ))}
          </select>
          {!loading && staff.length === 0 && (
            <p className="mt-1 text-xs text-amber-700">
              가입 신청 가능한 직원이 없습니다. 이미 가입했거나, 사장님이 아직
              등록하지 않았을 수 있어요.
            </p>
          )}
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-600">PIN (숫자 4자리)</label>
          <input
            type="password"
            inputMode="numeric"
            maxLength={4}
            className={field}
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 4))}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-600">PIN 확인</label>
          <input
            type="password"
            inputMode="numeric"
            maxLength={4}
            className={field}
            value={pin2}
            onChange={(e) => setPin2(e.target.value.replace(/\D/g, "").slice(0, 4))}
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={saving}
          className="w-full rounded bg-gray-900 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {saving ? "신청 중…" : "가입 신청"}
        </button>
      </form>
      <p className="mt-4 text-center text-xs text-gray-400">
        이미 가입했나요?{" "}
        <Link to="/staff-login" className="underline">
          로그인하기
        </Link>
      </p>
    </div>
  );
}
