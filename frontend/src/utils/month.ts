// 연차/사전휴무 신청 목록의 "월별 필터"에 쓰는 날짜 도우미.
// 날짜는 전부 "YYYY-MM-DD" 문자열이라, 이 형식끼리는 문자열 비교 = 날짜 비교라
// Date 객체(타임존 문제) 없이 그대로 비교해도 안전하다.

export const todayYm = (): string => new Date().toISOString().slice(0, 7); // "2026-09"

export function shiftYm(ym: string, delta: number): string {
  const [y, m] = ym.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function ymLabel(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  return `${y}년 ${m}월`;
}

// 신청 기간(start~end)이 특정 달(ym = "YYYY-MM")과 하루라도 겹치는지.
export function rangeOverlapsMonth(start: string, end: string, ym: string): boolean {
  const [y, m] = ym.split("-").map(Number);
  const monthStart = `${ym}-01`;
  const lastDay = new Date(y, m, 0).getDate(); // 그 달의 마지막 날짜
  const monthEnd = `${ym}-${String(lastDay).padStart(2, "0")}`;
  return start <= monthEnd && end >= monthStart;
}
