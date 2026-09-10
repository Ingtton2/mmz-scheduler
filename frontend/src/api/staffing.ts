// 필요 인원 설정 서버 통신 (스펙 4) — 포지션 x 시간대.
import { apiGet, apiSend } from "./client";

export interface StaffingItem {
  weekday: number; // 0=월 ~ 6=일
  position: "hall" | "kitchen";
  time_slot: "open" | "mid" | "close";
  min_headcount: number;
}

export const getStaffingRequirements = () =>
  apiGet<StaffingItem[]>("/staffing-requirements");

export const putStaffingRequirements = (items: StaffingItem[]) =>
  apiSend<StaffingItem[]>("PUT", "/staffing-requirements", { items });
