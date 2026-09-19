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

// --- 직원 셀프서비스 신청 가능 기간 (스펙 9-5) ------------------------------
// 백엔드 app/services/request_window.py 와 같은 규칙: 이번 달 20일 17시(한국시간)까지,
// "다음 달" 스케줄에 대해서만 신청 가능. 여기 값은 화면 안내용이고,
// 실제 허용 여부는 서버가 다시 검사한다.
export const SELF_SERVICE_CUTOFF_DAY = 20;
export const SELF_SERVICE_CUTOFF_HOUR = 17;

// 기기 시간대와 상관없이 한국시간(UTC+9, 서머타임 없음) 기준의 날짜/시각.
function kstParts(now: Date) {
  const k = new Date(now.getTime() + 9 * 60 * 60 * 1000);
  return {
    year: k.getUTCFullYear(),
    month: k.getUTCMonth() + 1,
    day: k.getUTCDate(),
    hour: k.getUTCHours(),
  };
}

export function selfServiceWindowOpen(today: Date = new Date()): boolean {
  const { day, hour } = kstParts(today);
  if (day !== SELF_SERVICE_CUTOFF_DAY) return day < SELF_SERVICE_CUTOFF_DAY;
  return hour < SELF_SERVICE_CUTOFF_HOUR;
}

// "다음 달"을 ym 문자열로.
export function selfServiceTargetYm(today: Date = new Date()): string {
  const { year, month } = kstParts(today);
  return shiftYm(`${year}-${String(month).padStart(2, "0")}`, 1);
}

// 오늘 날짜(한국시간). 기기 시간대와 상관없이 "YYYY-MM-DD" 와 연/월을 돌려준다.
export function todayKst(now: Date = new Date()): { year: number; month: number; iso: string } {
  const { year, month, day } = kstParts(now);
  const pad = (n: number) => String(n).padStart(2, "0");
  return { year, month, iso: `${year}-${pad(month)}-${pad(day)}` };
}
