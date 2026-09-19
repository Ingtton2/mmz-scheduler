// 자동배치 서버 통신 (스펙 5).
import { ApiError, apiGet, apiSend } from "./client";

export interface ScheduleWarning {
  date: string;
  position: string;
  needed: number;
  filled: number;
  message: string;
}

export interface ShiftSummary {
  open: number; // FO+BO
  mid: number; // BM
  close: number; // FC+BC
  full: number; // 풀오마 (파트타임)
  hall: number; // 홀 근무 일수
  kitchen: number; // 주방 근무 일수
  off: number;
  leave: number;
  blocked: number; // 사전 휴무 신청
  work: number;
}

export interface ScheduleRow {
  staff_id: number;
  staff_name: string;
  position: string;
  role: string;
  employment_type: string | null;
  cells: Record<string, string>; // "YYYY-MM-DD" -> 근무코드 (O/M/C/D-O/연차)
  summary: ShiftSummary;
}

export interface ScheduleResult {
  year: number;
  month: number;
  days: string[];
  rows: ScheduleRow[];
  warnings: ScheduleWarning[];
  feasible: boolean;
  solve_seconds: number;
  saved: boolean;
  edited: boolean;
  status: "draft" | "confirmed";
  share_code: string | null;
  published_at: string | null; // 직원에게 공개(공유)한 시각. 재공유 때마다 갱신.
  generated_at: string | null;
}

export interface ScheduleEdit {
  staff_id: number;
  work_date: string;
  work_code: string;
}

export interface ShareResult {
  share_code: string;
  published_at: string;
}

// 수동 수정에서 고를 수 있는 코드
export const EDIT_CODES = [
  "FO",
  "FC",
  "BO",
  "BM",
  "BC",
  "풀오마",
  "D/O",
  "연차",
  "사휴",
] as const;

// 직원별 이번 달 연차 사용 개수 (직원 id -> 개수). 날짜는 자동배치가 알아서 고른다.
export type LeaveDays = Record<number, number>;

export const runAutoSchedule = (year: number, month: number, leaveDays: LeaveDays = {}) =>
  apiSend<ScheduleResult>("POST", "/schedule/auto", { year, month, leave_days: leaveDays });

// 자동배치 화면의 연차 입력 패널용: 직원별 사용 가능한 잔여연차 + 이 달에 저장된 개수
export interface LeavePlanRow {
  staff_id: number;
  staff_name: string;
  remaining: number;
  saved_days: number;
}

export const getLeavePlan = (year: number, month: number) =>
  apiGet<LeavePlanRow[]>(`/schedule/leave-plan?year=${year}&month=${month}`);

export const editScheduleEntries = (
  year: number,
  month: number,
  changes: ScheduleEdit[],
) =>
  apiSend<ScheduleResult>("PATCH", "/schedule/entries", { year, month, changes });

export const shareSchedule = (year: number, month: number) =>
  apiSend<ShareResult>("POST", `/schedule/${year}/${month}/share`);

// 저장된 스케줄. 없으면 404 -> null
export async function getSavedSchedule(
  year: number,
  month: number,
): Promise<ScheduleResult | null> {
  try {
    return await apiGet<ScheduleResult>(
      `/schedule?year=${year}&month=${month}`,
    );
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}
