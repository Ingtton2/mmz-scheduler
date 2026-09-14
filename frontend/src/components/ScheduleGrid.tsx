// 근무표 그리드 + 범례 — 직원 QR 조회 화면(PublicSchedule)과 로그인한 직원의
// "이번 달 전체 스케줄"(MyTeamSchedulePage) 이 똑같은 모양이라 공용으로 뺐다.
import { CELL } from "../pages/SchedulePage";

const WD_CHAR = ["일", "월", "화", "수", "목", "금", "토"];
const parseWd = (s: string) => {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d).getDay();
};

export interface GridRow {
  staff_name: string;
  position: string;
  role: string;
  cells: Record<string, string>;
}

export function ScheduleLegend() {
  return (
    <div className="mb-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
      <span>
        <span className="rounded-full bg-mint px-1.5 py-0.5 font-semibold text-mint-ink">
          FO
        </span>{" "}
        홀오픈
      </span>
      <span>
        <span className="rounded-full bg-mint px-1.5 py-0.5 font-semibold text-mint-ink">
          FC
        </span>{" "}
        홀마감
      </span>
      <span>
        <span className="rounded-full bg-kitchen px-1.5 py-0.5 font-semibold text-kitchen-ink">
          BO
        </span>{" "}
        주방오픈
      </span>
      <span>
        <span className="rounded-full bg-kitchen px-1.5 py-0.5 font-semibold text-kitchen-ink">
          BM
        </span>{" "}
        주방미들
      </span>
      <span>
        <span className="rounded-full bg-kitchen px-1.5 py-0.5 font-semibold text-kitchen-ink">
          BC
        </span>{" "}
        주방마감
      </span>
      <span>
        <span className="rounded-full bg-[#F3E9D2] px-1.5 py-0.5 font-semibold text-primary">
          풀
        </span>{" "}
        풀오마
      </span>
      <span>
        <span className="rounded-full bg-gray-100 px-1.5 py-0.5 font-semibold text-gray-400">
          휴
        </span>{" "}
        휴무
      </span>
      <span>
        <span className="rounded-full bg-warn px-1.5 py-0.5 font-semibold text-warn-ink">
          연
        </span>{" "}
        연차
      </span>
    </div>
  );
}

export function ScheduleGrid({
  days,
  rows,
  highlightName,
}: {
  days: string[];
  rows: GridRow[];
  highlightName?: string;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border bg-white">
      <table className="border-collapse text-xs">
        <thead>
          <tr className="border-b bg-gray-50">
            <th className="sticky left-0 z-10 bg-gray-50 px-3 py-2 text-left font-medium">
              직원
            </th>
            {days.map((d) => {
              const wd = parseWd(d);
              const weekend = wd === 0 || wd === 6;
              return (
                <th
                  key={d}
                  className={
                    "w-8 px-0 py-1 text-center font-medium " +
                    (weekend ? "bg-amber-50 text-amber-700" : "")
                  }
                >
                  <div>{Number(d.split("-")[2])}</div>
                  <div className="text-[10px] text-gray-400">{WD_CHAR[wd]}</div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const mine = !!highlightName && row.staff_name === highlightName;
            return (
              <tr
                key={row.staff_name}
                className={"border-b last:border-0 " + (mine ? "bg-yellow-100" : "")}
              >
                <td
                  className={
                    "sticky left-0 z-10 px-3 py-1 font-medium whitespace-nowrap " +
                    (mine ? "bg-yellow-100" : "bg-white")
                  }
                >
                  {row.staff_name}
                </td>
                {days.map((d) => {
                  const code = row.cells[d] ?? "";
                  const meta = CELL[code];
                  return (
                    <td
                      key={d}
                      title={`${d} ${code}`}
                      className="w-8 border-l px-0.5 py-1 text-center"
                    >
                      {meta ? (
                        <span
                          className={
                            "inline-block w-full rounded-full px-1 py-0.5 text-[11px] leading-none font-semibold " +
                            meta.cls
                          }
                        >
                          {meta.short}
                        </span>
                      ) : (
                        <span className="text-gray-300">·</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
