// 직원 셀프서비스 API (스펙 9): 가입/로그인/PIN변경/내 연차·사전휴무/내 스케줄.
import { meGet, meSend } from "./meClient";
import type { PublicScheduleResult } from "./public";

export interface AvailableStaff {
  id: number;
  name: string;
  position: string;
  role: string;
}

export interface LoginableStaff {
  id: number;
  name: string;
}

export interface MyLeaveBalance {
  base_off_days: number;
  prev_remaining: number; // 전월잔여연차
  prev_accrued: number; // 전월발생연차
  used: number; // 사용연차
  total_accrued: number; // 총연차 (자동계산)
  remaining: number; // 잔여연차 (자동계산)
}

export interface MeInfo {
  id: number;
  name: string;
  role: string;
  position: string;
  employment_type: string | null;
  must_change_pin: boolean;
  leave: MyLeaveBalance | null; // 정직원·점장만 값이 있음
}

export interface LoginResult {
  token: string;
  must_change_pin: boolean;
  staff: MeInfo;
}

export const listAvailableForSignup = () =>
  meGet<AvailableStaff[]>("/public/staff-accounts/available");

export const signup = (staff_id: number, pin: string) =>
  meSend<{ status: string; message: string }>("POST", "/public/staff-accounts/signup", {
    staff_id,
    pin,
  });

export const listLoginable = () =>
  meGet<LoginableStaff[]>("/public/staff-accounts/login-list");

export const login = (staff_id: number, pin: string) =>
  meSend<LoginResult>("POST", "/public/staff-accounts/login", { staff_id, pin });

export const getMe = () => meGet<MeInfo>("/me");

export const changeMyPin = (current_pin: string, new_pin: string) =>
  meSend<{ ok: boolean }>("POST", "/me/change-pin", { current_pin, new_pin });

export interface MyRequest {
  id: number;
  start_date: string;
  end_date: string;
  days: number;
  note: string | null;
  created_at: string;
}

export interface MyLeaveRequest extends MyRequest {
  status: string;
}

export const listMyLeave = () => meGet<MyLeaveRequest[]>("/me/leave-requests");

export const createMyLeave = (start_date: string, end_date: string, note?: string) =>
  meSend<MyLeaveRequest>("POST", "/me/leave-requests", { start_date, end_date, note });

export const cancelMyLeave = (id: number) =>
  meSend<void>("DELETE", `/me/leave-requests/${id}`);

export const listMyDayOff = () => meGet<MyRequest[]>("/me/dayoff-requests");

export const createMyDayOff = (start_date: string, end_date: string, note?: string) =>
  meSend<MyRequest>("POST", "/me/dayoff-requests", { start_date, end_date, note });

export interface MyScheduleResult {
  year: number;
  month: number;
  days: string[];
  cells: Record<string, string>;
  summary: Record<string, number>;
  generated_at: string | null;
}

export const getMySchedule = (year: number, month: number) =>
  meGet<MyScheduleResult>(`/me/schedule/${year}/${month}`);

// 이번 달 전체 직원 스케줄 (동료 근무일 확인, 대타 부탁용). 공유된 스케줄만 보임.
export const getMyTeamSchedule = (year: number, month: number) =>
  meGet<PublicScheduleResult>(`/me/team-schedule/${year}/${month}`);
