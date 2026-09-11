// /me/... 라우트를 감싸는 문지기. 관리자용 RequireAuth 와 같은 패턴이지만
// - on/off 개념이 없음 (직원 셀프서비스는 항상 로그인 필요)
// - PIN 강제 변경(must_change_pin) 이면 /me/change-pin 으로 보냄 (스펙 9-3)
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getMe } from "./api/me";
import { clearStaffToken, getStaffToken } from "./api/meClient";

type Status = "checking" | "ok" | "must-change-pin" | "login";

export default function RequireStaffAuth({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [status, setStatus] = useState<Status>("checking");
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const slowTimer = setTimeout(() => {
      if (!cancelled) setSlow(true);
    }, 4000);

    async function check() {
      if (!getStaffToken()) {
        if (!cancelled) setStatus("login");
        return;
      }
      try {
        const me = await getMe();
        if (!cancelled) setStatus(me.must_change_pin ? "must-change-pin" : "ok");
      } catch {
        clearStaffToken();
        if (!cancelled) setStatus("login");
      }
    }

    setStatus("checking");
    setSlow(false);
    check();
    return () => {
      cancelled = true;
      clearTimeout(slowTimer);
    };
  }, [location.pathname]);

  useEffect(() => {
    function onExpired() {
      setStatus("login");
    }
    window.addEventListener("mmz-staff-auth-expired", onExpired);
    return () => window.removeEventListener("mmz-staff-auth-expired", onExpired);
  }, []);

  if (status === "checking") {
    return (
      <div className="p-8 text-sm text-gray-400">
        확인 중...
        {slow && (
          <p className="mt-2 text-gray-400">
            서버가 잠들어 있다가 깨는 중일 수 있어요 (최대 1분 정도 걸릴 수 있습니다).
          </p>
        )}
      </div>
    );
  }
  if (status === "login") {
    return <Navigate to="/staff-login" state={{ from: location.pathname }} replace />;
  }
  if (status === "must-change-pin" && location.pathname !== "/me/change-pin") {
    return <Navigate to="/me/change-pin" replace />;
  }
  return <>{children}</>;
}
