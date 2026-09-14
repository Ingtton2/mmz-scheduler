// 직원 조회 전용 화면 (스펙 6.2 / 7). QR 스캔 -> /schedule/{공유코드}.
// 로그인 없이 그 달 근무표를 표(이미지 형태)로 보여준다.
// 스케줄이 "공유됨" 상태일 때만 보이고, 임시(초안) 상태면 서버가 막는다.
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { getPublicSchedule, type PublicScheduleResult } from "../api/public";
import { ScheduleGrid, ScheduleLegend } from "../components/ScheduleGrid";

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
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "스케줄을 불러오지 못했습니다."),
      )
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
          {error || "스케줄을 찾을 수 없습니다. 링크가 만료되었거나 잘못되었어요."}
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

      <ScheduleLegend />
      <ScheduleGrid days={data.days} rows={data.rows} highlightName={q.trim()} />

      <p className="mt-3 text-center text-xs text-gray-400">
        스크린샷으로 저장하거나 인쇄해서 보관하세요.
      </p>
    </div>
  );
}
