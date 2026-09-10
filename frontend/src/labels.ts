// 서버가 쓰는 영어 코드 <-> 화면에 보여줄 한글 이름 매핑.
// (스펙 2.1 / 2.2)

export const EMPLOYMENT_TYPES = [
  { value: "full_time", label: "정직원" },
  { value: "part_time", label: "파트타임" },
] as const;

export const POSITIONS = [
  { value: "hall", label: "홀 전담" },
  { value: "kitchen", label: "주방 전담" },
  { value: "both", label: "겸직 (홀+주방)" },
] as const;

export const ROLES = [
  { value: "staff", label: "일반 직원" },
  { value: "manager", label: "점장" },
  { value: "owner", label: "사장님" },
] as const;

export const TIME_SLOTS = [
  { value: "open", label: "오픈" },
  { value: "mid", label: "미들" },
  { value: "close", label: "마감" },
] as const;

const toMap = (arr: readonly { value: string; label: string }[]) =>
  Object.fromEntries(arr.map((o) => [o.value, o.label]));

export const LEAVE_STATUS = [
  { value: "requested", label: "신청" },
  { value: "confirmed", label: "확정" },
] as const;

// 0 = 월요일 ... 6 = 일요일  (파이썬 date.weekday() 와 동일)
export const WEEKDAYS = [
  { value: 0, label: "월" },
  { value: 1, label: "화" },
  { value: 2, label: "수" },
  { value: 3, label: "목" },
  { value: 4, label: "금" },
  { value: 5, label: "토" },
  { value: 6, label: "일" },
] as const;

export const LABEL = {
  employment: toMap(EMPLOYMENT_TYPES),
  position: toMap(POSITIONS),
  role: toMap(ROLES),
  leaveStatus: toMap(LEAVE_STATUS),
};
