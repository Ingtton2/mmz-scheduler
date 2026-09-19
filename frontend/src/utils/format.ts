// 연차/사전휴무 신청 화면에서 공통으로 쓰는 표시용 포맷터.

export function fmtRange(start: string, end: string, days: number): string {
  return start === end ? start : `${start} ~ ${end} (${days}일)`;
}

// 서버는 UTC 시각을 "2026-09-16T06:38:00" 처럼 시간대 표시 없이 내려준다. new Date() 는 이걸
// 기기 로컬 시간으로 잘못 읽으므로, UTC 로 고정해 읽은 뒤 한국시간(KST)으로 보여준다.
export function fmtKstDateTime(iso: string): string {
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(iso);
  const utcMs = new Date(hasZone ? iso : `${iso}Z`).getTime();
  const k = new Date(utcMs + 9 * 60 * 60 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${k.getUTCFullYear()}-${pad(k.getUTCMonth() + 1)}-${pad(k.getUTCDate())} ${pad(k.getUTCHours())}:${pad(k.getUTCMinutes())}`;
}

export const fmtKstDate = (iso: string): string => fmtKstDateTime(iso).slice(0, 10);
