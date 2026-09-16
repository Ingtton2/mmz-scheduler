// "연차 관리 > 연차 사용 현황" 탭 (스펙 3, 4단계).
//  - 이번 달 부여 대상 카드 (입사일 기준 자동 계산)
//  - 전 직원 연차 사용 현황 표
//  - 부여 이력 / 사용 이력 로그
import { useEffect, useState } from "react";
import { listStaff, type Staff } from "../api/staff";
import {
  createGrant,
  listGrantCandidates,
  listGrantLog,
  listUsageLog,
  type GrantCandidate,
  type LeaveGrant,
  type LeaveUsageLogEntry,
} from "../api/leaveUsage";

const fmtDays = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

const KIND_TEXT: Record<GrantCandidate["kind"], { desc: string; button: string }> = {
  monthly: { desc: "입사 1년 미만 · 만근 확인 대상", button: "월차 1개 부여" },
  anniversary: { desc: "입사 1주년 도달", button: "연차 15일 부여" },
};

export default function LeaveUsageTab() {
  const [staff, setStaff] = useState<Staff[]>([]);
  const [candidates, setCandidates] = useState<GrantCandidate[]>([]);
  const [grantLog, setGrantLog] = useState<LeaveGrant[]>([]);
  const [usageLog, setUsageLog] = useState<LeaveUsageLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [grantingId, setGrantingId] = useState<number | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const [s, c, g, u] = await Promise.all([
        listStaff(),
        listGrantCandidates(),
        listGrantLog(),
        listUsageLog(),
      ]);
      setStaff(s);
      setCandidates(c);
      setGrantLog(g);
      setUsageLog(u);
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

  async function handleGrant(c: GrantCandidate) {
    setGrantingId(c.staff_id);
    try {
      await createGrant({
        staff_id: c.staff_id,
        days: c.days,
        note: c.kind === "anniversary" ? "1주년 연차부여" : "월차 자동부여",
      });
      setError("");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setGrantingId(null);
    }
  }

  const staffWithLeave = staff.filter((s) => s.leave != null);

  return (
    <div className="space-y-6">
      {error && (
        <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      {/* --- 이번 달 부여 대상 --- */}
      <section>
        <h2 className="mb-2 text-sm font-semibold text-gray-700">이번 달 부여 대상</h2>
        {loading ? (
          <p className="rounded-lg border bg-white p-4 text-sm text-gray-400">불러오는 중…</p>
        ) : candidates.length === 0 ? (
          <p className="rounded-lg border bg-white p-4 text-sm text-gray-400">
            이번 달 부여 대상이 없습니다.
          </p>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {candidates.map((c) => (
              <li
                key={c.staff_id}
                className="flex items-center justify-between rounded-lg border bg-white p-4"
              >
                <div>
                  <div className="font-semibold">{c.staff_name}</div>
                  <div className="text-xs text-gray-400">
                    입사일 {c.hire_date} · {KIND_TEXT[c.kind].desc}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleGrant(c)}
                  disabled={grantingId === c.staff_id}
                  className="rounded bg-primary hover:bg-primary-dark px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
                >
                  {grantingId === c.staff_id ? "부여 중…" : KIND_TEXT[c.kind].button}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* --- 전 직원 연차 사용 현황 --- */}
      <section>
        <h2 className="mb-2 text-sm font-semibold text-gray-700">전 직원 연차 사용 현황</h2>
        <div className="overflow-x-auto rounded-lg border bg-white">
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50 text-left text-gray-500">
              <tr>
                <th className="px-3 py-2">이름</th>
                <th className="px-3 py-2 text-right">부여연차</th>
                <th className="px-3 py-2 text-right">사용연차</th>
                <th className="px-3 py-2 text-right">잔여연차</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-gray-400">
                    불러오는 중…
                  </td>
                </tr>
              ) : staffWithLeave.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-gray-400">
                    연차 관리 대상 직원이 없습니다.
                  </td>
                </tr>
              ) : (
                staffWithLeave.map((s) => (
                  <tr key={s.id} className="border-b last:border-0">
                    <td className="px-3 py-2 font-medium">{s.name}</td>
                    <td className="px-3 py-2 text-right">{fmtDays(s.leave!.granted)}</td>
                    <td className="px-3 py-2 text-right">{fmtDays(s.leave!.used)}</td>
                    <td className="px-3 py-2 text-right font-semibold">
                      {fmtDays(s.leave!.remaining)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* --- 부여 이력 --- */}
      <section>
        <h2 className="mb-2 text-sm font-semibold text-gray-700">부여 이력</h2>
        <div className="overflow-x-auto rounded-lg border bg-white">
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50 text-left text-gray-500">
              <tr>
                <th className="px-3 py-2">날짜</th>
                <th className="px-3 py-2">대상자</th>
                <th className="px-3 py-2 text-right">부여일수</th>
                <th className="px-3 py-2">메모</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-gray-400">
                    불러오는 중…
                  </td>
                </tr>
              ) : grantLog.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-gray-400">
                    아직 부여 이력이 없습니다.
                  </td>
                </tr>
              ) : (
                grantLog.map((g) => (
                  <tr key={g.id} className="border-b last:border-0">
                    <td className="px-3 py-2 whitespace-nowrap">{g.granted_at}</td>
                    <td className="px-3 py-2">{g.staff_name}</td>
                    <td className="px-3 py-2 text-right">{fmtDays(g.days)}일</td>
                    <td className="px-3 py-2 text-gray-600">{g.note ?? ""}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* --- 사용 이력 --- */}
      <section>
        <h2 className="mb-2 text-sm font-semibold text-gray-700">사용 이력</h2>
        <p className="mb-2 text-xs text-gray-400">
          "신청 승인" 탭에서 연차를 승인하면 자동으로 기록됩니다.
        </p>
        <div className="overflow-x-auto rounded-lg border bg-white">
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50 text-left text-gray-500">
              <tr>
                <th className="px-3 py-2">직원명</th>
                <th className="px-3 py-2">사용일</th>
                <th className="px-3 py-2 text-right">사용일수</th>
                <th className="px-3 py-2">신청일</th>
                <th className="px-3 py-2 text-right">사용 후 잔여연차</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-center text-gray-400">
                    불러오는 중…
                  </td>
                </tr>
              ) : usageLog.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-center text-gray-400">
                    아직 사용 이력이 없습니다.
                  </td>
                </tr>
              ) : (
                usageLog.map((u) => (
                  <tr key={u.id} className="border-b last:border-0">
                    <td className="px-3 py-2 font-medium">{u.staff_name}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {u.start_date === u.end_date
                        ? u.start_date
                        : `${u.start_date} ~ ${u.end_date}`}
                    </td>
                    <td className="px-3 py-2 text-right">{fmtDays(u.days)}일</td>
                    <td className="px-3 py-2 whitespace-nowrap text-gray-500">{u.applied_at}</td>
                    <td className="px-3 py-2 text-right font-semibold">
                      {fmtDays(u.remaining_after)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
