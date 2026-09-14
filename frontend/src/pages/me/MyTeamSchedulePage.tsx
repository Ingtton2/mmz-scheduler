// 이번 달 전체 직원 스케줄 (스펙 9-4 확장) — 동료 근무일 확인, 대타 부탁용.
// 공유(confirmed)된 스케줄만 보인다. 본인 이름은 자동으로 강조됨.
import { useEffect, useState } from "react";
import { getMe, getMyTeamSchedule, type MeInfo } from "../../api/me";
import { MeApiError } from "../../api/meClient";
import { ScheduleGrid, ScheduleLegend } from "../../components/ScheduleGrid";
import type { PublicScheduleResult } from "../../api/public";
import MeNav from "./MeNav";

function thisYm(): { year: number; month: number } {
  const now = new Date();
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

function shift(year: number, month: number, delta: number): { year: number; month: number } {
  const d = new Date(year, month - 1 + delta, 1);
  return { year: d.getFullYear(), month: d.getMonth() + 1 };
}

export default function MyTeamSchedulePage() {
  const [{ year, month }, setYm] = useState(thisYm());
  const [me, setMe] = useState<MeInfo | null>(null);
  const [data, setData] = useState<PublicScheduleResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    setError("");
    getMyTeamSchedule(year, month)
      .then(setData)
      .catch((e) => {
        setData(null);
        setError(e instanceof MeApiError ? e.message : "불러오기 실패");
      })
      .finally(() => setLoading(false));
  }, [year, month]);

  return (
    <div>
      <MeNav current="전체 스케줄" />
      <h1 className="mb-1 text-xl font-bold">이번 달 전체 스케줄</h1>
      <p className="mb-4 text-sm text-gray-500">
        동료 근무일 확인, 대타 부탁할 때 참고하세요. 사장님이 아직 공유하지
        않은 달은 안 보여요.
      </p>

      <div className="mb-4 flex items-center gap-2">
        <button
          onClick={() => setYm(shift(year, month, -1))}
          className="rounded border px-2 py-1 text-sm hover:bg-gray-50"
        >
          ← 이전달
        </button>
        <span className="min-w-[6rem] text-center text-sm font-semibold">
          {year}년 {month}월
        </span>
        <button
          onClick={() => setYm(shift(year, month, 1))}
          className="rounded border px-2 py-1 text-sm hover:bg-gray-50"
        >
          다음달 →
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">불러오는 중…</p>
      ) : error || !data ? (
        <p className="rounded-lg border bg-white p-6 text-center text-sm text-gray-600">
          {error || "아직 스케줄이 공유되지 않았습니다."}
        </p>
      ) : (
        <>
          <ScheduleLegend />
          <ScheduleGrid days={data.days} rows={data.rows} highlightName={me?.name} />
        </>
      )}
    </div>
  );
}
