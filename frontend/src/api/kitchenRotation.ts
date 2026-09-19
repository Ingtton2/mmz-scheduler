// 주방 오픈/미들/마감 3인 월별 로테이션 미리보기/저장 ("근무표 관리" 자동배치 화면).
import { apiGet, apiSend } from "./client";

export type RotationSlot = "open" | "mid" | "close";

export interface RotationItem {
  staff_id: number;
  staff_name: string;
  position: RotationSlot;
}

export interface RotationPreview {
  year: number;
  month: number;
  items: RotationItem[];
  saved: boolean; // false = 전월 기준으로 방금 계산만 한 미리보기
}

export const SLOT_LABEL: Record<RotationSlot, string> = {
  open: "오픈",
  mid: "미들",
  close: "마감",
};

export const getRotation = (year: number, month: number) =>
  apiGet<RotationPreview>(`/kitchen-rotation?year=${year}&month=${month}`);

export const saveRotation = (
  year: number,
  month: number,
  items: { staff_id: number; position: RotationSlot }[],
) => apiSend<RotationPreview>("PUT", "/kitchen-rotation", { year, month, items });
