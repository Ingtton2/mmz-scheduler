// 근무표 그리드 + 범례 — 로그인한 직원의 "이번 달 전체 스케줄"
// (MyTeamSchedulePage) 화면에서 쓰는 공용 컴포넌트.
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

const LEGEND_ITEMS: { code: string; cls: string; label: string; time?: string }[] = [
  { code: "FO", cls: "bg-fo text-fo-ink", label: "홀오픈", time: "10:45~20:45" },
  { code: "FC", cls: "bg-fc text-fc-ink", label: "홀마감", time: "11:30~21:30" },
  { code: "BO", cls: "bg-bo text-bo-ink", label: "주방오픈", time: "10:30~20:30" },
  { code: "BM", cls: "bg-bm text-bm-ink", label: "주방미들", time: "11:00~21:00" },
  { code: "BC", cls: "bg-bc text-bc-ink", label: "주방마감", time: "11:30~21:30" },
  { code: "풀", cls: "bg-full text-full-ink", label: "풀오마 (하루 종일)" },
  { code: "휴", cls: "bg-off text-off-ink", label: "휴무 (D/O)" },
  { code: "연", cls: "bg-leave text-leave-ink", label: "연차" },
  { code: "사", cls: "bg-dayoff text-dayoff-ink", label: "사전휴무" },
];

export function ScheduleLegend() {
  return (
    <div className="mb-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
      {LEGEND_ITEMS.map((item) => (
        <span key={item.code}>
          <span
            className={"rounded-full px-1.5 py-0.5 font-semibold " + item.cls}
          >
            {item.code}
          </span>{" "}
          {item.label}
          {item.time ? ` ${item.time}` : ""}
        </span>
      ))}
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
