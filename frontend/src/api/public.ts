// 직원 조회 전용 (로그인 없음, 스펙 6.2).
import { apiGet } from "./client";

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

export const getPublicSchedule = (shareCode: string) =>
  apiGet<PublicScheduleResult>(`/public/schedule/${shareCode}`);
