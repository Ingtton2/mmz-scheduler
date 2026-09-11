// 백엔드(서버)에 요청을 보내는 얇은 도우미.
//  - 로컬 개발: vite.config.ts 의 proxy 가 "/api" 를 localhost:8000 으로 전달
//  - 배포(Vercel): vercel.json 의 rewrite 가 "/api" 를 Render 백엔드로 전달 (같은 출처라 CORS 불필요)
//  - 필요하면 VITE_API_BASE 로 백엔드 주소를 직접 지정할 수도 있음 (이 경우 백엔드 CORS 설정 필요)
export const API_BASE: string =
  import.meta.env.VITE_API_BASE?.replace(/\/$/, "") || "/api";
const BASE = API_BASE;

// --- 관리자 로그인 토큰 (스펙 9 간이 버전) ---------------------------------
// ADMIN_USER/ADMIN_PASS 가 서버에 설정돼 있을 때만 실제로 쓰인다.
// 브라우저에만 저장되고(localStorage), 매 요청마다 Authorization 헤더로 붙는다.
const TOKEN_KEY = "mmz_admin_token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null; // 프라이빗 창 등에서 localStorage 가 막혀있을 수 있음
  }
}

export function setToken(token: string) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* 저장 실패해도 앱이 죽지 않게 무시 */
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* noop */
  }
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parse<T>(res: Response, label: string): Promise<T> {
  if (res.status === 401) {
    // 토큰이 없거나 만료됨 → 로그인 화면으로 보내야 함을 앱 전체에 알림 (RequireAuth 가 구독).
    clearToken();
    window.dispatchEvent(new Event("mmz-auth-expired"));
  }
  if (!res.ok) {
    // FastAPI 는 오류 시 {"detail": "..."} 형태를 줍니다. 그 메시지를 최대한 살림.
    let detail = `${label} 실패 (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail =
          typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail);
      }
    } catch {
      /* 본문이 비어있을 수 있음 */
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T; // No Content
  return (await res.json()) as T;
}

export async function apiGet<T>(path: string): Promise<T> {
  return parse<T>(
    await fetch(`${BASE}${path}`, { headers: authHeaders() }),
    `GET ${path}`,
  );
}

export async function apiSend<T>(
  method: "POST" | "PUT" | "PATCH" | "DELETE",
  path: string,
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return parse<T>(res, `${method} ${path}`);
}
