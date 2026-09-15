// 직원 관련 서버 통신.
import { apiGet, apiSend } from "./client";

// 연차 정보 (스펙 3). 정직원만 값이 있고, 파트타임/사장님은 null.
export interface LeaveBalance {
  base_off_days: number;
  prev_remaining: number;
  prev_accrued: number;
  used: number;
  total_accrued: number; // 합연차 (자동)
  remaining: number; // 잔여연차 (자동)
}

export interface LeaveBalanceInput {
  base_off_days: number;
  prev_remaining: number;
  prev_accrued: number;
  used: number;
}

export interface Staff {
  id: number;
  store_id: number;
  name: string;
  employment_type: string | null; // 사장님이면 null
  position: string;
  role: string;
  work_weekdays: number[]; // 0=월 ~ 6=일
  fixed_schedule: boolean; // 근무 가능 요일에 항상 배치
  is_active: boolean;
  hire_date: string | null; // "YYYY-MM-DD"
  created_at: string;
  leave: LeaveBalance | null; // 정직원만
}

export interface StaffCreate {
  name: string;
  position: string;
  role: string;
  employment_type?: string | null;
  work_weekdays: number[];
  fixed_schedule: boolean;
  hire_date?: string | null;
  leave: LeaveBalanceInput;
}

export interface StaffUpdate {
  name?: string;
  position?: string;
  role?: string;
  employment_type?: string | null;
  work_weekdays?: number[];
  fixed_schedule?: boolean;
  hire_date?: string | null;
}

export const listStaff = () => apiGet<Staff[]>("/staff");

export const createStaff = (data: StaffCreate) =>
  apiSend<Staff>("POST", "/staff", data);

export const updateStaff = (id: number, data: StaffUpdate) =>
  apiSend<Staff>("PATCH", `/staff/${id}`, data);

export const updateLeaveBalance = (id: number, data: LeaveBalanceInput) =>
  apiSend<Staff>("PATCH", `/staff/${id}/leave`, data);

export const deleteStaff = (id: number) =>
  apiSend<void>("DELETE", `/staff/${id}`);
