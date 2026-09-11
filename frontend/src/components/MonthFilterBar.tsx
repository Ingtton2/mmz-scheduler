// 연차/사전휴무 신청 목록 위에 붙는 "월별 보기" 내비게이션.
// month === null 이면 "전체 보기" 상태.
import { shiftYm, todayYm, ymLabel } from "../utils/month";

export default function MonthFilterBar({
  month,
  onChange,
  total,
  shown,
}: {
  month: string | null;
  onChange: (ym: string | null) => void;
  total: number;
  shown: number;
}) {
  const current = month ?? todayYm();

  return (
    <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border bg-white px-3 py-2">
      <button
        type="button"
        onClick={() => onChange(shiftYm(current, -1))}
        className="rounded border px-2 py-1 text-sm hover:bg-gray-50"
      >
        ← 이전달
      </button>
      <span className="min-w-[6rem] text-center text-sm font-semibold">
        {month === null ? "전체" : ymLabel(month)}
      </span>
      <button
        type="button"
        onClick={() => onChange(shiftYm(current, 1))}
        className="rounded border px-2 py-1 text-sm hover:bg-gray-50"
      >
        다음달 →
      </button>
      <button
        type="button"
        onClick={() => onChange(month === null ? todayYm() : null)}
        className={
          "ml-1 rounded px-2 py-1 text-sm " +
          (month === null
            ? "bg-primary hover:bg-primary-dark text-white"
            : "border text-gray-600 hover:bg-gray-50")
        }
      >
        전체 보기
      </button>
      <span className="ml-auto text-xs text-gray-400">
        {shown}건 표시 {month !== null && `· 전체 ${total}건`}
      </span>
    </div>
  );
}
