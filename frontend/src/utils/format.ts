// 연차/사전휴무 신청 화면에서 공통으로 쓰는 표시용 포맷터.

export function fmtRange(start: string, end: string, days: number): string {
  return start === end ? start : `${start} ~ ${end} (${days}일)`;
}
