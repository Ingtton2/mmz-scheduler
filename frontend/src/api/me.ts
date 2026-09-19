// 직원 셀프서비스 API (스펙 9): 가입/로그인/PIN변경/내 연차·사전휴무/내 스케줄.
import { meGet, meSend } from "./meClient";
import type { HolidayItem } from "./holiday";
import type { LeaveGrant, LeaveUsageLogEntry } from "./leaveUsage";
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
  granted: number; // 부여연차 (누적)
  used: number; // 사용연차 (누적)
  remaining: number; // 잔여연차 (자동계산: 부여 - 사용)
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
  status: string; // requested(신청) / confirmed(확정) / rejected(반려)
  reject_reason: string | null; // 반려일 때 사장님이 적은 사유
  note: string | null;
  created_at: string;
}

export const listMyDayOff = () => meGet<MyRequest[]>("/me/dayoff-requests");

export const deleteMyDayOff = (id: number) =>
  meSend<void>("DELETE", `/me/dayoff-requests/${id}`);

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

// 관리자가 등록한 공휴일 — 내 스케줄 달력에 이름을 표시하는 용도.
export const getMyHolidays = () => meGet<HolidayItem[]>("/me/holidays");

// 내 연차 부여 이력 / 사용 이력 (최신순) — "내 연차" 화면용.
export const listMyLeaveGrants = () => meGet<LeaveGrant[]>("/me/leave-grants");
export const listMyLeaveUsages = () => meGet<LeaveUsageLogEntry[]>("/me/leave-usages");
