// 연차 신청 관련 서버 통신 (스펙 3) — 기간(시작일~종료일) 단위.
import { apiGet, apiSend } from "./client";

export interface LeaveRequest {
  id: number;
  staff_id: number;
  staff_name: string;
  start_date: string; // "YYYY-MM-DD"
  end_date: string;
  days: number; // 기간 일수 (양끝 포함)
  status: "requested" | "confirmed";
  note: string | null;
  created_at: string;
}

export interface LeaveRequestCreate {
  staff_id: number;
  start_date: string;
  end_date: string;
  note?: string | null;
  status?: "requested" | "confirmed";
}

export const listLeaveRequests = () => apiGet<LeaveRequest[]>("/leave-requests");

export const createLeaveRequest = (data: LeaveRequestCreate) =>
  apiSend<LeaveRequest>("POST", "/leave-requests", data);

export const updateLeaveRequest = (
  id: number,
  data: Partial<
    Pick<LeaveRequest, "status" | "note" | "start_date" | "end_date">
  >,
) => apiSend<LeaveRequest>("PATCH", `/leave-requests/${id}`, data);

export const deleteLeaveRequest = (id: number) =>
  apiSend<void>("DELETE", `/leave-requests/${id}`);
