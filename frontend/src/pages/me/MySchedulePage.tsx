// 내 스케줄 조회 (스펙 9-4). 본인 칸만 달력으로 보여준다 — 팀 전체 표는 "전체 스케줄" 메뉴(MyTeamSchedulePage)에서.
import { useEffect, useState } from "react";
import { getMyHolidays, getMySchedule, type MyScheduleResult } from "../../api/me";
import { MeApiError } from "../../api/meClient";
import { canGoPrevMonth, todayKst } from "../../utils/month";
import { CELL } from "../SchedulePage";
import MeNav from "./MeNav";

const WD_CHAR = ["일", "월", "화", "수", "목", "금", "토"];
const pad = (n: number) => String(n).padStart(2, "0");

function thisYm(): { year: number; month: number } {
  const { year, month } = todayKst();
  return { year, month };
}

function shift(year: number, month: number, delta: number): { year: number; month: number } {
  const d = new Date(year, month - 1 + delta, 1);
  return { year: d.getFullYear(), month: d.getMonth() + 1 };
}

// 그 달의 달력 칸 목록: 1일 앞은 빈 칸(null), 마지막 주도 7칸으로 채운다.
function calendarCells(year: number, month: number): (string | null)[] {
  const firstWd = new Date(year, month - 1, 1).getDay();
  const lastDay = new Date(year, month, 0).getDate();
  const cells: (string | null)[] = Array(firstWd).fill(null);
  for (let d = 1; d <= lastDay; d++) cells.push(`${year}-${pad(month)}-${pad(d)}`);
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

// 달력 칸은 넓어서 관리자 표(좁은 칸)보다 뱃지 글자를 풀어서 쓴다. 여기 없는 코드는 CELL 의 짧은 글자 그대로.
const BADGE_TEXT: Record<string, string> = { "D/O": "휴무", 연차: "연차", 사휴: "사휴" };

const wdColor = (wd: number) =>
  wd === 0 ? "text-red-500" : wd === 6 ? "text-blue-500" : "text-gray-700";

export default function MySchedulePage() {
  const [{ year, month }, setYm] = useState(thisYm());
  const [data, setData] = useState<MyScheduleResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const todayIso = todayKst().iso;
  const isCurrentMonth = `${year}-${pad(month)}` === todayIso.slice(0, 7);
  const cells = calendarCells(year, month);
  // 공휴일(날짜 -> 이름). 표시 전용이라 못 불러와도 달력은 그대로 보여준다.
  const [holidays, setHolidays] = useState<Record<string, string>>({});

  useEffect(() => {
    getMyHolidays()
      .then((list) => setHolidays(Object.fromEntries(list.map((h) => [h.date, h.name]))))
      .catch(() => {});
  }, []);

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
          disabled={!canGoPrevMonth(year, month)}
          className="rounded border px-2 py-1 text-sm hover:bg-gray-50 disabled:cursor-default disabled:text-gray-300 disabled:hover:bg-transparent"
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
        <button
          onClick={() => setYm(thisYm())}
          disabled={isCurrentMonth}
          className="rounded border border-[#B08968] px-2 py-1 text-sm font-medium text-[#B08968] hover:bg-amber-50 disabled:cursor-default disabled:border-gray-200 disabled:text-gray-300 disabled:hover:bg-transparent"
        >
          오늘
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
            <div className="grid grid-cols-7 border-b bg-gray-50 text-center text-xs font-medium">
              {WD_CHAR.map((w, wd) => (
                <div key={w} className={"py-2 " + wdColor(wd)}>
                  {w}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7">
              {cells.map((d, i) => {
                const wd = i % 7;
                const isLastRow = i >= cells.length - 7;
                const base =
                  "flex min-h-[3.5rem] flex-col items-center gap-1 px-0.5 py-1 " +
                  (wd !== 6 ? "border-r " : "") +
                  (isLastRow ? "" : "border-b ");
                if (!d) return <div key={`blank-${i}`} className={base + "bg-gray-50/50"} />;

                const code = data.cells[d];
                const meta = code ? CELL[code] : undefined;
                const isToday = d === todayIso;
                const holidayName = holidays[d];
                return (
                  <div
                    key={d}
                    title={holidayName}
                    className={base + (isToday ? "bg-amber-50" : "")}
                  >
                    <span
                      className={
                        "flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-xs " +
                        (isToday
                          ? "bg-[#B08968] font-semibold text-white"
                          : holidayName
                            ? wdColor(0)
                            : wdColor(wd))
                      }
                    >
                      {Number(d.slice(8))}
                    </span>
                    {code ? (
                      <span
                        className={
                          "rounded-full px-1.5 py-0.5 text-[11px] leading-none font-semibold " +
                          (meta?.cls ?? "bg-gray-100 text-gray-600")
                        }
                      >
                        {BADGE_TEXT[code] ?? meta?.short ?? code}
                      </span>
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                    {holidayName && (
                      <span className="line-clamp-2 px-0.5 text-center text-[8px] leading-tight break-all text-red-500">
                        {holidayName}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
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
