// "휴가 일정 공유" 메모판 — 순수 참고용 (연차·사전휴무 신청과 무관).
// 직원은 meClient(직원 토큰), 관리자는 client(관리자 토큰)로 같은 모양의 데이터를 받는다.
import { apiGet } from "./client";
import { meGet, meSend } from "./meClient";

export interface DateRange {
  start: string; // YYYY-MM-DD
  end: string; // YYYY-MM-DD (포함)
}

export interface VacationNote {
  staff_id: number;
  name: string;
  months: string[]; // YYYY-MM
  ranges: DateRange[];
  no_plans: boolean;
  memo: string;
  updated_at: string;
}

export interface VacationBoard {
  months: string[]; // 화면에 보여줄 달 (이번 달 ~ 2027-12)
  today: string; // YYYY-MM-DD (한국시간)
  notes: VacationNote[];
  my_staff_id: number | null;
  my_name: string | null;
  can_edit: boolean;
}

export interface VacationNoteSave {
  months: string[];
  ranges: DateRange[];
  no_plans: boolean;
  memo: string;
}

export const getMyVacationBoard = () => meGet<VacationBoard>("/me/vacation-notes");

export const saveMyVacationNote = (body: VacationNoteSave) =>
  meSend<VacationNote | null>("PUT", "/me/vacation-notes/mine", body);

export const getVacationBoard = () => apiGet<VacationBoard>("/vacation-notes");
