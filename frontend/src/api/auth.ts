// 관리자 로그인 API (스펙 9 간이 버전 — 사장님 1명, 아이디/비밀번호).
import { apiGet, apiSend } from "./client";

export interface AuthStatus {
  enabled: boolean; // 서버에 ADMIN_USER/ADMIN_PASS 가 설정돼 있는지 (꺼져 있으면 로그인 없이 통과)
}

export interface LoginResult {
  token: string;
}

export function getAuthStatus(): Promise<AuthStatus> {
  return apiGet<AuthStatus>("/auth/status");
}

export function login(username: string, password: string): Promise<LoginResult> {
  return apiSend<LoginResult>("POST", "/auth/login", { username, password });
}

export function checkSession(): Promise<{ ok: boolean }> {
  return apiGet<{ ok: boolean }>("/auth/me");
}

export function logout(): Promise<{ ok: boolean }> {
  return apiSend<{ ok: boolean }>("POST", "/auth/logout");
}
