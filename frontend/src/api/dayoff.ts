// 사전 휴무 신청 서버 통신 (스펙 3.1) — 연차와 별개, 기간 단위, 월 20일 한도.
import { apiGet, apiSend } from "./client";

export const MAX_PER_MONTH = 20;

export interface DayOffRequest {
  id: number;
  staff_id: number;
  staff_name: string;
  start_date: string; // "YYYY-MM-DD"
  end_date: string;
  days: number;
  note: string | null;
  created_at: string;
}

export interface DayOffRequestCreate {
  staff_id: number;
  start_date: string;
  end_date: string;
  note?: string | null;
}

export const listDayOffRequests = () =>
  apiGet<DayOffRequest[]>("/dayoff-requests");

export const createDayOffRequest = (data: DayOffRequestCreate) =>
  apiSend<DayOffRequest>("POST", "/dayoff-requests", data);

export const deleteDayOffRequest = (id: number) =>
  apiSend<void>("DELETE", `/dayoff-requests/${id}`);
