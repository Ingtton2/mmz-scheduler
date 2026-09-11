// 관리자용: 직원 셀프서비스 계정 승인/거절/PIN 초기화 (스펙 9-2, 9-3).
import { apiGet, apiSend } from "./client";

export interface PendingAccount {
  account_id: number;
  staff_id: number;
  staff_name: string;
  position: string;
  role: string;
  created_at: string;
}

export interface Account {
  account_id: number;
  staff_id: number;
  staff_name: string;
  status: string; // "pending" | "approved"
  must_change_pin: boolean;
  created_at: string;
  approved_at: string | null;
}

export interface OwnerWithoutAccount {
  id: number;
  name: string;
  position: string;
  role: string;
}

export const listAccounts = () => apiGet<Account[]>("/staff-accounts");

export const listPendingAccounts = () => apiGet<PendingAccount[]>("/staff-accounts/pending");

// 사장님은 공개 가입 목록(/join)엔 안 보이므로, 관리자 화면에서 대신 계정을 만들어준다.
export const listOwnersWithoutAccount = () =>
  apiGet<OwnerWithoutAccount[]>("/staff-accounts/owners-without-account");

export const approveAccount = (accountId: number) =>
  apiSend<Account>("POST", `/staff-accounts/${accountId}/approve`);

export const rejectAccount = (accountId: number) =>
  apiSend<void>("POST", `/staff-accounts/${accountId}/reject`);

export const resetPin = (staffId: number) =>
  apiSend<{ temp_pin: string }>("POST", `/staff-accounts/reset-pin/${staffId}`);
