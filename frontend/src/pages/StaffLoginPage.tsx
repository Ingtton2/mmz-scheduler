// 직원 셀프서비스 로그인 (스펙 9). 이름 선택(동명이인 방지) + PIN.
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { listLoginable, login, type LoginableStaff } from "../api/me";
import { MeApiError, setStaffToken } from "../api/meClient";
import logo from "../assets/logo.png";

export default function StaffLoginPage() {
  const [staff, setStaff] = useState<LoginableStaff[]>([]);
  const [staffId, setStaffId] = useState("");
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    listLoginable()
      .then(setStaff)
      .catch((e) => setError(e instanceof Error ? e.message : "불러오기 실패"))
      .finally(() => setLoading(false));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!staffId) return setError("이름을 선택해 주세요.");
    setSaving(true);
    try {
      const res = await login(Number(staffId), pin);
      setStaffToken(res.token);
      if (res.must_change_pin) {
        navigate("/me/change-pin", { replace: true });
      } else {
        const from = (location.state as { from?: string } | null)?.from || "/me";
        navigate(from, { replace: true });
      }
    } catch (err) {
      setError(err instanceof MeApiError ? err.message : "로그인에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  const field = "w-full rounded border border-gray-300 px-3 py-2 text-sm";

  return (
    <div className="mx-auto mt-16 max-w-sm rounded-lg border bg-white p-6 shadow-sm">
      <img src={logo} alt="memeal.zip" className="mx-auto mb-4 h-16 w-16 rounded" />
      <h1 className="mb-1 text-center text-lg font-bold">직원 로그인</h1>
      <p className="mb-5 text-center text-sm text-gray-500">
        이름을 선택하고 PIN을 입력하세요.
      </p>
      <form onSubmit={onSubmit} className="space-y-3">
        <div>
          <label className="mb-1 block text-sm text-gray-600">이름</label>
          <select
            className={field}
            value={staffId}
            onChange={(e) => setStaffId(e.target.value)}
            disabled={loading}
            autoFocus
          >
            <option value="">{loading ? "불러오는 중…" : "선택하세요"}</option>
            {staff.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          {!loading && staff.length === 0 && (
            <p className="mt-1 text-xs text-amber-700">
              아직 승인된 계정이 없습니다.{" "}
              <Link to="/join" className="underline">
                가입 신청
              </Link>
              을 먼저 해주세요.
            </p>
          )}
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-600">PIN</label>
          <input
            type="password"
            inputMode="numeric"
            maxLength={4}
            className={field}
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 4))}
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={saving}
          className="w-full rounded bg-primary hover:bg-primary-dark py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {saving ? "로그인 중…" : "로그인"}
        </button>
      </form>
      <p className="mt-4 text-center text-xs text-gray-400">
        처음이신가요?{" "}
        <Link to="/join" className="underline">
          가입 신청하기
        </Link>
      </p>
    </div>
  );
}
