// 내 연차 조회. 연차는 직원이 날짜로 신청하지 않는다 — 사장님이 부여하고, 근무표를 만들 때
// 직원별 사용 개수를 정하면 자동배치가 날짜를 골라 넣는다. 여기서는 잔여연차만 확인.
import { useEffect, useState } from "react";
import {
  getMe,
  listMyLeaveGrants,
  listMyLeaveUsages,
  type MeInfo,
} from "../../api/me";
import type { LeaveGrant, LeaveUsageLogEntry } from "../../api/leaveUsage";
import { fmtRange } from "../../utils/format";
import MeNav from "./MeNav";

const fmtDays = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

export default function MyLeavePage() {
  const [me, setMe] = useState<MeInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [grants, setGrants] = useState<LeaveGrant[]>([]);
  const [usages, setUsages] = useState<LeaveUsageLogEntry[]>([]);

  useEffect(() => {
    Promise.all([getMe(), listMyLeaveGrants(), listMyLeaveUsages()])
      .then(([meInfo, g, u]) => {
        setMe(meInfo);
        setGrants(g);
        setUsages(u);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "불러오기 실패"))
      .finally(() => setLoading(false));
  }, []);

  const isPartTime = me?.employment_type === "part_time";
  const leave = me?.leave ?? null;
  const usedPct =
    leave && leave.granted > 0
      ? Math.min(100, Math.max(0, Math.round((leave.used / leave.granted) * 100)))
      : 0;

  return (
    <div>
      <MeNav current="내 연차" />
      <h1 className="mb-1 text-xl font-bold">내 연차</h1>
      <p className="mb-4 text-sm text-gray-500">
        연차는 사장님이 부여하고, 근무표를 만들 때 사용할 개수를 정해서 자동으로 넣어줘요.
        쉬는 날은 내 스케줄의 “연” 표시로 확인하세요.
      </p>

      {error && (
        <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      {isPartTime && (
        <p className="mb-4 rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">
          파트타임은 연차 대상이 아닙니다.
        </p>
      )}

      {loading && <p className="text-sm text-gray-400">불러오는 중…</p>}

      {leave && (
        <div className="mb-4 rounded-lg border bg-white p-5">
          <div className="text-center">
            <div className="text-xs text-gray-500">잔여연차</div>
            <div className="text-4xl font-bold text-[#B08968]">
              {fmtDays(leave.remaining)}일
            </div>
          </div>

          <div className="mt-4">
            <div className="mb-1 flex justify-between text-xs text-gray-500">
              <span>사용 {fmtDays(leave.used)}일</span>
              <span>총 {fmtDays(leave.granted)}일</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
              <div
                className="h-full rounded-full bg-[#B08968]"
                style={{ width: `${usedPct}%` }}
              />
            </div>
          </div>

          <dl className="mt-4 grid grid-cols-2 gap-y-1.5 border-t pt-3 text-sm">
            <dt className="text-gray-500">부여연차</dt>
            <dd className="text-right">{fmtDays(leave.granted)}일</dd>
            <dt className="text-gray-500">사용연차</dt>
            <dd className="text-right">{fmtDays(leave.used)}일</dd>
            <dt className="font-medium text-gray-700">잔여연차</dt>
            <dd className="text-right font-medium">{fmtDays(leave.remaining)}일</dd>
          </dl>
        </div>
      )}

      {leave && (
        <>
          <section className="mb-4">
            <h2 className="mb-2 text-sm font-semibold text-gray-700">연차 사용 내역</h2>
            <div className="overflow-x-auto rounded-lg border bg-white">
              <table className="w-full text-sm">
                <thead className="border-b bg-gray-50 text-left text-gray-500">
                  <tr>
                    <th className="px-3 py-2">사용일</th>
                    <th className="px-3 py-2 text-right">일수</th>
                    <th className="px-3 py-2 text-right">사용 후 잔여</th>
                  </tr>
                </thead>
                <tbody>
                  {usages.length === 0 ? (
                    <tr>
                      <td colSpan={3} className="px-3 py-6 text-center text-gray-400">
                        아직 사용한 연차가 없어요.
                      </td>
                    </tr>
                  ) : (
                    usages.map((u) => (
                      <tr key={u.id} className="border-b last:border-0">
                        <td className="px-3 py-2">
                          {u.year_month ? (
                            <>
                              <span className="text-xs text-gray-400">{u.year_month} 근무표</span>
                              <div className="whitespace-nowrap">
                                {u.dates.map((d) => d.slice(5)).join(", ") || "-"}
                              </div>
                            </>
                          ) : (
                            <span className="whitespace-nowrap">
                              {fmtRange(u.start_date, u.end_date, u.days)}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-right">{fmtDays(u.days)}일</td>
                        <td className="px-3 py-2 text-right font-semibold">
                          {fmtDays(u.remaining_after)}일
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="mb-4">
            <h2 className="mb-2 text-sm font-semibold text-gray-700">연차 부여 내역</h2>
            <div className="overflow-x-auto rounded-lg border bg-white">
              <table className="w-full text-sm">
                <thead className="border-b bg-gray-50 text-left text-gray-500">
                  <tr>
                    <th className="px-3 py-2">부여일</th>
                    <th className="px-3 py-2 text-right">부여일수</th>
                    <th className="px-3 py-2">내용</th>
                  </tr>
                </thead>
                <tbody>
                  {grants.length === 0 ? (
                    <tr>
                      <td colSpan={3} className="px-3 py-6 text-center text-gray-400">
                        아직 부여된 연차가 없어요.
                      </td>
                    </tr>
                  ) : (
                    grants.map((g) => (
                      <tr key={g.id} className="border-b last:border-0">
                        <td className="px-3 py-2 whitespace-nowrap">{g.granted_at}</td>
                        <td className="px-3 py-2 text-right">{fmtDays(g.days)}일</td>
                        <td className="px-3 py-2 text-gray-600">{g.note ?? ""}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
