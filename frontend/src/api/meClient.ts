// 직원 셀프서비스 전용 저수준 통신 도우미 (client.ts 와 같은 패턴이지만 완전히 별도).
// 관리자 토큰과 절대 섞이면 안 되므로 - 다른 localStorage 키, 다른 만료 이벤트를 쓴다.
import { API_BASE } from "./client";

const TOKEN_KEY = "mmz_staff_token";

export function getStaffToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setStaffToken(token: string) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* noop */
  }
}

export function clearStaffToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* noop */
  }
}

function authHeaders(): Record<string, string> {
  const token = getStaffToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export class MeApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "MeApiError";
    this.status = status;
  }
}

const REQUEST_TIMEOUT_MS = 55_000;

async function timedFetch(url: string, init: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new MeApiError("서버 응답이 너무 오래 걸려요. 잠시 후 다시 시도해주세요.", 0);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

async function parse<T>(res: Response, label: string): Promise<T> {
  if (res.status === 401) {
    clearStaffToken();
    window.dispatchEvent(new Event("mmz-staff-auth-expired"));
  }
  if (!res.ok) {
    let detail = `${label} 실패 (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail =
          typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* 본문이 비어있을 수 있음 */
    }
    throw new MeApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function meGet<T>(path: string): Promise<T> {
  return parse<T>(
    await timedFetch(`${API_BASE}${path}`, { headers: authHeaders() }),
    `GET ${path}`,
  );
}

export async function meSend<T>(
  method: "POST" | "PUT" | "PATCH" | "DELETE",
  path: string,
  body?: unknown,
): Promise<T> {
  const res = await timedFetch(`${API_BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return parse<T>(res, `${method} ${path}`);
}
