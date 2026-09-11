// 관리자용: 직원 셀프서비스 계정 승인/거절 + PIN 초기화 (스펙 9-2, 9-3).
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  approveAccount,
  listAccounts,
  listPendingAccounts,
  rejectAccount,
  resetPin,
  type Account,
  type PendingAccount,
} from "../api/staffAccounts";
import { LABEL } from "../labels";

export default function StaffAccountsPage() {
  const [pending, setPending] = useState<PendingAccount[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [tempPin, setTempPin] = useState<{ staffId: number; pin: string } | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const [p, a] = await Promise.all([listPendingAccounts(), listAccounts()]);
      setPending(p);
      setAccounts(a);
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

  async function onApprove(accountId: number) {
    setBusyId(accountId);
    try {
      await approveAccount(accountId);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "승인 실패");
    } finally {
      setBusyId(null);
    }
  }

  async function onReject(accountId: number) {
    setBusyId(accountId);
    try {
      await rejectAccount(accountId);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "거절 실패");
    } finally {
      setBusyId(null);
    }
  }

  async function onResetPin(staffId: number) {
    setBusyId(staffId);
    setTempPin(null);
    try {
      const res = await resetPin(staffId);
      setTempPin({ staffId, pin: res.temp_pin });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "PIN 초기화 실패");
    } finally {
      setBusyId(null);
    }
  }

  const approved = accounts.filter((a) => a.status === "approved");

  return (
    <div>
      <div className="mb-4 flex items-center gap-2 text-sm text-gray-500">
        <Link to="/admin" className="hover:underline">
          관리자 홈
        </Link>
        <span>/</span>
        <span className="text-gray-800">직원 계정 승인/PIN 관리</span>
      </div>

      <h1 className="mb-1 text-xl font-bold">직원 계정 승인/PIN 관리</h1>
      <p className="mb-6 text-sm text-gray-500">
        직원이 <code className="rounded bg-gray-100 px-1">/join</code> 에서 가입 신청하면
        여기 승인 대기 목록에 뜹니다. 승인해야 직원이 로그인할 수 있어요. PIN을
        잊어버렸다고 하면 아래에서 초기화해 주세요.
      </p>

      {error && (
        <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      <h2 className="mb-2 text-sm font-semibold text-gray-700">
        승인 대기 ({pending.length})
      </h2>
      <div className="mb-8 overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="px-3 py-2">이름</th>
              <th className="px-3 py-2">역할</th>
              <th className="px-3 py-2">포지션</th>
              <th className="px-3 py-2">신청일</th>
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
            ) : pending.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-gray-400">
                  승인 대기 중인 신청이 없습니다.
                </td>
              </tr>
            ) : (
              pending.map((p) => (
                <tr key={p.account_id} className="border-b last:border-0">
                  <td className="px-3 py-2 font-medium">{p.staff_name}</td>
                  <td className="px-3 py-2">{LABEL.role[p.role] ?? p.role}</td>
                  <td className="px-3 py-2">{LABEL.position[p.position] ?? p.position}</td>
                  <td className="px-3 py-2 text-gray-500">
                    {p.created_at.slice(0, 10)}
                  </td>
                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    <button
                      onClick={() => onApprove(p.account_id)}
                      disabled={busyId === p.account_id}
                      className="rounded bg-gray-900 px-2 py-1 text-xs text-white disabled:opacity-50"
                    >
                      승인
                    </button>
                    <button
                      onClick={() => onReject(p.account_id)}
                      disabled={busyId === p.account_id}
                      className="ml-2 text-xs text-red-600 hover:underline disabled:opacity-50"
                    >
                      거절
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <h2 className="mb-2 text-sm font-semibold text-gray-700">
        가입된 직원 계정 ({approved.length})
      </h2>
      {tempPin && (
        <p className="mb-3 rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">
          새 임시 PIN: <b className="text-base">{tempPin.pin}</b> — 이 직원에게 알려주세요.
          (다시 조회할 수 없으니 지금 전달하세요. 로그인하면 새 PIN으로 바꾸도록 안내됩니다.)
        </p>
      )}
      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="px-3 py-2">이름</th>
              <th className="px-3 py-2">가입일</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={3} className="px-3 py-6 text-center text-gray-400">
                  불러오는 중…
                </td>
              </tr>
            ) : approved.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-3 py-6 text-center text-gray-400">
                  아직 가입된 직원 계정이 없습니다.
                </td>
              </tr>
            ) : (
              approved.map((a) => (
                <tr key={a.account_id} className="border-b last:border-0">
                  <td className="px-3 py-2 font-medium">{a.staff_name}</td>
                  <td className="px-3 py-2 text-gray-500">
                    {(a.approved_at ?? a.created_at).slice(0, 10)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      onClick={() => onResetPin(a.staff_id)}
                      disabled={busyId === a.staff_id}
                      className="text-xs text-gray-600 hover:underline disabled:opacity-50"
                    >
                      PIN 초기화
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-xs text-gray-400">
        직원 가입 링크: <code className="rounded bg-gray-100 px-1">/join</code> · 직원 로그인:{" "}
        <code className="rounded bg-gray-100 px-1">/staff-login</code>
      </p>
    </div>
  );
}
