// 내 스케줄 조회 (스펙 9-4). 본인 칸만 보여준다 — 팀 전체 표는 "전체 스케줄" 메뉴(MyTeamSchedulePage)에서.
import { useEffect, useState } from "react";
import { getMySchedule, type MyScheduleResult } from "../../api/me";
import { MeApiError } from "../../api/meClient";
import { CELL } from "../SchedulePage";
import MeNav from "./MeNav";

const WD_CHAR = ["일", "월", "화", "수", "목", "금", "토"];
const parseWd = (s: string) => {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d).getDay();
};

function thisYm(): { year: number; month: number } {
  const now = new Date();
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

function shift(year: number, month: number, delta: number): { year: number; month: number } {
  const d = new Date(year, month - 1 + delta, 1);
  return { year: d.getFullYear(), month: d.getMonth() + 1 };
}

export default function MySchedulePage() {
  const [{ year, month }, setYm] = useState(thisYm());
  const [data, setData] = useState<MyScheduleResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError("");
    getMySchedule(year, month)
      .then(setData)
      .catch((e) => {
        setData(null);
        setError(e instanceof MeApiError ? e.message : "불러오기 실패");
      })
      .finally(() => setLoading(false));
  }, [year, month]);

  return (
    <div>
      <MeNav current="내 스케줄" />
      <h1 className="mb-4 text-xl font-bold">내 스케줄</h1>

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
      ) : error ? (
        <p className="rounded-lg border bg-white p-6 text-center text-sm text-gray-600">
          {error}
        </p>
      ) : data && data.days.length > 0 ? (
        <>
          <div className="mb-4 flex flex-wrap gap-2 text-xs text-gray-500">
            <span className="rounded bg-gray-50 px-2 py-1">근무 {data.summary.work ?? 0}일</span>
            <span className="rounded bg-gray-50 px-2 py-1">휴무 {data.summary.off ?? 0}일</span>
            <span className="rounded bg-gray-50 px-2 py-1">연차 {data.summary.leave ?? 0}일</span>
            <span className="rounded bg-gray-50 px-2 py-1">사휴 {data.summary.blocked ?? 0}일</span>
          </div>
          <div className="overflow-hidden rounded-lg border bg-white">
            {data.days.map((d) => {
              const code = data.cells[d];
              const meta = code ? CELL[code] : undefined;
              const wd = parseWd(d);
              return (
                <div
                  key={d}
                  className="flex items-center justify-between border-b px-3 py-2 text-sm last:border-0"
                >
                  <span
                    className={
                      wd === 0 ? "text-red-500" : wd === 6 ? "text-blue-500" : "text-gray-700"
                    }
                  >
                    {d.slice(5)} ({WD_CHAR[wd]})
                  </span>
                  {code ? (
                    <span className={"rounded-full px-2 py-0.5 text-xs font-semibold " + (meta?.cls ?? "")}>
                      {meta?.short ?? code}
                    </span>
                  ) : (
                    <span className="text-xs text-gray-300">—</span>
                  )}
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <p className="rounded-lg border bg-white p-6 text-center text-sm text-gray-400">
          아직 이 달 스케줄이 없습니다.
        </p>
      )}
    </div>
  );
}
