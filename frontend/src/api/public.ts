// 직원 전체 스케줄 조회에 쓰는 공용 타입 (로그인 후, api/me.ts 의
// getMyTeamSchedule 응답 모양). 백엔드 schedule_view.build_public_view() 가
// 조립하는 모양과 대응된다.

export interface PublicRow {
  staff_name: string;
  position: string;
  role: string;
  cells: Record<string, string>;
}

export interface PublicScheduleResult {
  year: number;
  month: number;
  store_name: string;
  days: string[];
  rows: PublicRow[];
  generated_at: string | null;
}
