// 연차 부여/사용 현황 서버 통신 ("연차 관리 > 연차 사용 현황" 탭).
import { apiGet, apiSend } from "./client";

export interface GrantCandidate {
  staff_id: number;
  staff_name: string;
  hire_date: string;
  kind: "monthly" | "anniversary"; // monthly = 월차 1개, anniversary = 1주년 15일
  days: number;
}

export interface LeaveGrantCreate {
  staff_id: number;
  days: number;
  note?: string | null;
  granted_at?: string | null; // 비우면 서버가 오늘 날짜로 저장
}

export interface LeaveGrant {
  id: number;
  staff_id: number;
  staff_name: string;
  granted_at: string;
  days: number;
  note: string | null;
}

export interface LeaveUsageLogEntry {
  id: number;
  staff_id: number;
  staff_name: string;
  start_date: string;
  end_date: string;
  days: number;
  applied_at: string;
  remaining_after: number;
  // 자동배치 방식 사용 이력이면 "YYYY-MM" + 실제 연차로 잡힌 날짜들. 예전 승인 방식 이력은 null/빈 배열.
  year_month: string | null;
  dates: string[];
}

export const listGrantCandidates = () =>
  apiGet<GrantCandidate[]>("/leave/grant-candidates");

export const createGrant = (data: LeaveGrantCreate) =>
  apiSend<LeaveGrant>("POST", "/leave/grants", data);

export const listGrantLog = () => apiGet<LeaveGrant[]>("/leave/grant-log");

export const listUsageLog = () => apiGet<LeaveUsageLogEntry[]>("/leave/usage-log");
