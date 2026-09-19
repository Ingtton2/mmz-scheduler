// 목록 페이징 — 한 페이지 10개, 10개를 넘을 때만 나타난다.
export const PAGE_SIZE = 10;

// 삭제·필터로 목록이 줄어 현재 페이지가 없어졌을 때 마지막 페이지로 맞춘다.
export function clampPage(page: number, total: number): number {
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  return Math.min(Math.max(1, page), totalPages);
}

export function paginate<T>(items: T[], page: number): T[] {
  const p = clampPage(page, items.length);
  return items.slice((p - 1) * PAGE_SIZE, p * PAGE_SIZE);
}

export default function Pagination({
  page,
  total,
  onChange,
}: {
  page: number;
  total: number;
  onChange: (page: number) => void;
}) {
  if (total <= PAGE_SIZE) return null;

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const current = clampPage(page, total);
  const first = Math.max(1, Math.min(current - 2, totalPages - 4));
  const last = Math.min(totalPages, first + 4);
  const numbers = Array.from({ length: last - first + 1 }, (_, i) => first + i);

  const base = "rounded border px-2.5 py-1 text-sm";
  return (
    <nav aria-label="페이지 이동" className="mt-3 flex flex-wrap items-center justify-center gap-1">
      <button
        type="button"
        onClick={() => onChange(current - 1)}
        disabled={current === 1}
        className={base + " hover:bg-gray-50 disabled:cursor-default disabled:text-gray-300 disabled:hover:bg-transparent"}
      >
        ← 이전
      </button>
      {numbers.map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          aria-current={n === current ? "page" : undefined}
          className={
            base +
            (n === current
              ? " border-primary bg-primary font-semibold text-white"
              : " hover:bg-gray-50")
          }
        >
          {n}
        </button>
      ))}
      <button
        type="button"
        onClick={() => onChange(current + 1)}
        disabled={current === totalPages}
        className={base + " hover:bg-gray-50 disabled:cursor-default disabled:text-gray-300 disabled:hover:bg-transparent"}
      >
        다음 →
      </button>
    </nav>
  );
}
