// 공휴일(대체공휴일 포함) 등록 서버 통신 — 관리자가 직접 날짜 등록, 스케줄표 표시 전용.
import { apiGet, apiSend } from "./client";

export interface HolidayItem {
  id: number;
  date: string; // YYYY-MM-DD
  name: string;
}

export const getHolidays = () => apiGet<HolidayItem[]>("/holidays");

export const createHoliday = (date: string, name: string) =>
  apiSend<HolidayItem>("POST", "/holidays", { date, name });

export const deleteHoliday = (id: number) =>
  apiSend<void>("DELETE", `/holidays/${id}`);
