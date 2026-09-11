// 직원 조회 전용 화면 (스펙 6.2 / 7). QR 스캔 -> /schedule/{공유코드}.
// 로그인 없이 그 달 근무표를 표(이미지 형태)로 보여준다.
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { getPublicSchedule, type PublicScheduleResult } from "../api/public";
import { CELL } from "./SchedulePage";

const WD_CHAR = ["일", "월", "화", "수", "목", "금", "토"];
const parseWd = (s: string) => {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d).getDay();
};

export default function PublicSchedule() {
  const { shareCode } = useParams();
  const [data, setData] = useState<PublicScheduleResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");

  useEffect(() => {
    if (!shareCode) return;
    getPublicSchedule(shareCode)
      .then(setData)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [shareCode]);

  const names = useMemo(
    () => (data ? data.rows.map((r) => r.staff_name) : []),
    [data],
  );

  if (loading)
    return <p className="p-6 text-center text-sm text-gray-400">불러오는 중…</p>;
  if (error || !data)
    return (
      <div className="rounded-lg border bg-white p-6 text-center">
        <p className="text-sm text-gray-600">
          스케줄을 찾을 수 없습니다. 링크가 만료되었거나 잘못되었어요.
        </p>
      </div>
    );

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-lg font-bold">
          {data.store_name} · {data.year}년 {data.month}월 근무표
        </h1>
        <input
          list="staff-names"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="내 이름 입력하면 강조"
          className="rounded border border-gray-300 px-2 py-1 text-sm"
        />
        <datalist id="staff-names">
          {names.map((n) => (
            <option key={n} value={n} />
          ))}
        </datalist>
      </div>

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

      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="border-collapse text-xs">
          <thead>
            <tr className="border-b bg-gray-50">
              <th className="sticky left-0 z-10 bg-gray-50 px-3 py-2 text-left font-medium">
                직원
              </th>
              {data.days.map((d) => {
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
            {data.rows.map((row) => {
              const mine = q.trim() !== "" && row.staff_name === q.trim();
              return (
                <tr
                  key={row.staff_name}
                  className={
                    "border-b last:border-0 " + (mine ? "bg-yellow-100" : "")
                  }
                >
                  <td
                    className={
                      "sticky left-0 z-10 px-3 py-1 font-medium whitespace-nowrap " +
                      (mine ? "bg-yellow-100" : "bg-white")
                    }
                  >
                    {row.staff_name}
                  </td>
                  {data.days.map((d) => {
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

      <p className="mt-3 text-center text-xs text-gray-400">
        스크린샷으로 저장하거나 인쇄해서 보관하세요.
      </p>
    </div>
  );
}
