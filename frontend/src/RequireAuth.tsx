// /admin/... 라우트를 감싸서 로그인 여부를 확인하는 문지기 컴포넌트.
// - 서버에 ADMIN_USER/ADMIN_PASS 가 없으면(enabled: false) 로그인 없이 그냥 통과 (로컬 개발용).
// - 있으면 토큰이 있는지 + 실제로 아직 유효한지(/auth/me) 확인하고, 아니면 /login 으로 보냄.
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { checkSession, getAuthStatus } from "./api/auth";
import { clearToken, getToken } from "./api/client";

type Status = "checking" | "ok" | "login";

export default function RequireAuth({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const { enabled } = await getAuthStatus();
        if (!enabled) {
          if (!cancelled) setStatus("ok");
          return;
        }
        if (!getToken()) {
          if (!cancelled) setStatus("login");
          return;
        }
        await checkSession();
        if (!cancelled) setStatus("ok");
      } catch {
        clearToken();
        if (!cancelled) setStatus("login");
      }
    }

    setStatus("checking");
    check();
    return () => {
      cancelled = true;
    };
  }, [location.pathname]);

  // client.ts 가 어디서든 401 을 받으면 이 이벤트를 쏜다 (예: 로그인 도중 토큰 만료).
  useEffect(() => {
    function onExpired() {
      setStatus("login");
    }
    window.addEventListener("mmz-auth-expired", onExpired);
    return () => window.removeEventListener("mmz-auth-expired", onExpired);
  }, []);

  if (status === "checking") {
    return <div className="p-8 text-sm text-gray-400">확인 중...</div>;
  }
  if (status === "login") {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return <>{children}</>;
}
