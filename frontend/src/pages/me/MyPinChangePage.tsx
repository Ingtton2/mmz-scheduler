// PIN 변경 (스펙 9-3). 사장님이 PIN을 초기화한 뒤엔 강제로 여기로 오게 됨.
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { changeMyPin, getMe } from "../../api/me";
import { MeApiError } from "../../api/meClient";
import MeNav from "./MeNav";

export default function MyPinChangePage() {
  const [forced, setForced] = useState(false);
  const [currentPin, setCurrentPin] = useState("");
  const [newPin, setNewPin] = useState("");
  const [newPin2, setNewPin2] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    getMe()
      .then((me) => setForced(me.must_change_pin))
      .catch(() => {});
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (newPin.length !== 4 || !/^\d{4}$/.test(newPin)) {
      return setError("새 PIN은 숫자 4자리여야 합니다.");
    }
    if (newPin !== newPin2) return setError("새 PIN이 서로 일치하지 않습니다.");
    setSaving(true);
    try {
      await changeMyPin(currentPin, newPin);
      setDone(true);
      setTimeout(() => navigate("/me", { replace: true }), 1200);
    } catch (err) {
      setError(err instanceof MeApiError ? err.message : "변경에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  const field = "w-full rounded border border-gray-300 px-3 py-2 text-sm";

  return (
    <div>
      <MeNav current="PIN 변경" />
      <div className="mx-auto max-w-sm rounded-lg border bg-white p-6">
        <h1 className="mb-1 text-lg font-bold">PIN 변경</h1>
        {forced ? (
          <p className="mb-4 text-sm text-amber-700">
            사장님이 PIN을 초기화했어요. 새 PIN을 설정해야 계속 쓸 수 있습니다.
          </p>
        ) : (
          <p className="mb-4 text-sm text-gray-500">현재 PIN 확인 후 새 PIN으로 바꿉니다.</p>
        )}
        {done ? (
          <p className="text-sm text-green-700">변경 완료! 이동합니다…</p>
        ) : (
          <form onSubmit={onSubmit} className="space-y-3">
            <div>
              <label className="mb-1 block text-sm text-gray-600">현재 PIN</label>
              <input
                type="password"
                inputMode="numeric"
                maxLength={4}
                className={field}
                value={currentPin}
                onChange={(e) => setCurrentPin(e.target.value.replace(/\D/g, "").slice(0, 4))}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-gray-600">새 PIN (숫자 4자리)</label>
              <input
                type="password"
                inputMode="numeric"
                maxLength={4}
                className={field}
                value={newPin}
                onChange={(e) => setNewPin(e.target.value.replace(/\D/g, "").slice(0, 4))}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-gray-600">새 PIN 확인</label>
              <input
                type="password"
                inputMode="numeric"
                maxLength={4}
                className={field}
                value={newPin2}
                onChange={(e) => setNewPin2(e.target.value.replace(/\D/g, "").slice(0, 4))}
              />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button
              type="submit"
              disabled={saving}
              className="w-full rounded-lg bg-[#B08968] hover:bg-[#997555] py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {saving ? "변경 중…" : "PIN 변경"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
