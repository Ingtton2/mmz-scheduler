// 휴가 일정 공유 — 날짜/구간 계산 도우미 (프로토타입 로직 그대로).
import type { DateRange } from "../../api/vacationNotes";

export const pad = (n: number) => String(n).padStart(2, "0");
export const yOf = (k: string) => +k.slice(0, 4);
export const mOf = (k: string) => +k.slice(5, 7);
export const dOf = (d: string) => +d.slice(8, 10);

export function addDay(d: string, n: number): string {
  const t = new Date(yOf(d), mOf(d) - 1, dOf(d) + n);
  return `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}`;
}

/** 겹치거나 붙어 있는 구간을 하나로 합친다. */
export function mergeRanges(list: DateRange[]): DateRange[] {
  const out: DateRange[] = [];
  [...list]
    .sort((a, b) => (a.start < b.start ? -1 : a.start > b.start ? 1 : 0))
    .forEach((r) => {
      const last = out[out.length - 1];
      if (last && r.start <= addDay(last.end, 1)) {
        if (r.end > last.end) last.end = r.end;
      } else out.push({ start: r.start, end: r.end });
    });
  return out;
}

export const rangesIn = (ranges: DateRange[], k: string) =>
  ranges.filter((r) => r.start.slice(0, 7) === k);

export const rText = (r: DateRange) =>
  r.start === r.end ? `${dOf(r.start)}일` : `${dOf(r.start)}–${dOf(r.end)}일`;

export const periodLabel = (months: string[]) =>
  months.length
    ? `${yOf(months[0])}년 ${mOf(months[0])}월 ~ ${yOf(months[months.length - 1])}년 ${mOf(months[months.length - 1])}월`
    : "";

/** 달 목록을 연도별로 묶는다 (그리드에 "2026년" 머리글을 달기 위해). */
export function byYear(months: string[]): [number, string[]][] {
  const m = new Map<number, string[]>();
  months.forEach((k) => {
    const y = yOf(k);
    if (!m.has(y)) m.set(y, []);
    m.get(y)!.push(k);
  });
  return [...m.entries()];
}
