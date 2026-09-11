// 최상위 화면 + 주소(URL)별 화면 분기.
// 스펙 6장의 두 종류 화면을 여기서 나눕니다.
import { useEffect, useState } from "react";
import {
  Routes,
  Route,
  Link,
  Navigate,
  useLocation,
  useNavigate,
} from "react-router-dom";
import AdminHome from "./pages/AdminHome";
import StaffPage from "./pages/StaffPage";
import LeavePage from "./pages/LeavePage";
import DayOffPage from "./pages/DayOffPage";
import StaffingPage from "./pages/StaffingPage";
import SchedulePage from "./pages/SchedulePage";
import PublicSchedule from "./pages/PublicSchedule";
import LoginPage from "./pages/LoginPage";
import RequireAuth from "./RequireAuth";
import { getAuthStatus, logout as apiLogout } from "./api/auth";
import { clearToken, getToken } from "./api/client";

function LogoutButton() {
  const [enabled, setEnabled] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    getAuthStatus()
      .then((s) => setEnabled(s.enabled))
      .catch(() => setEnabled(false));
  }, []);

  // 로그인 기능이 꺼져있거나, 로그인 화면이거나, 아직 로그인 전이면 버튼을 안 보여줌.
  if (!enabled || location.pathname === "/login" || !getToken()) return null;

  async function onClick() {
    try {
      await apiLogout();
    } catch {
      /* 이미 만료됐어도 어차피 로그아웃이 목적이므로 무시 */
    }
    clearToken();
    navigate("/login", { replace: true });
  }

  return (
    <button
      onClick={onClick}
      className="text-sm text-gray-500 hover:text-gray-800"
    >
      로그아웃
    </button>
  );
}

export default function App() {
  const location = useLocation();
  // 직원 조회 화면(QR)·로그인 화면은 관리자 헤더(로그아웃 버튼 등) 없이 깔끔하게 보여준다.
  const isAdminChrome = !location.pathname.startsWith("/schedule/");

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      {isAdminChrome && (
        <header className="flex items-center justify-between border-b bg-white px-4 py-3">
          <Link to="/admin" className="font-bold">
            mmz-scheduler
          </Link>
          <LogoutButton />
        </header>
      )}

      <main className="mx-auto max-w-6xl p-4">
        <Routes>
          {/* 관리자 로그인 (스펙 9 간이 버전) */}
          <Route path="/login" element={<LoginPage />} />

          {/* 사장님용 (관리자) — 스펙 6.1. 로그인 설정이 켜져 있으면 로그인 필요. */}
          <Route
            path="/admin"
            element={
              <RequireAuth>
                <AdminHome />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/staff"
            element={
              <RequireAuth>
                <StaffPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/leave"
            element={
              <RequireAuth>
                <LeavePage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/dayoff"
            element={
              <RequireAuth>
                <DayOffPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/staffing"
            element={
              <RequireAuth>
                <StaffingPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/schedule"
            element={
              <RequireAuth>
                <SchedulePage />
              </RequireAuth>
            }
          />

          {/* 직원 조회 전용 — QR 로 접속. 로그인 없음 — 스펙 6.2 */}
          <Route path="/schedule/:shareCode" element={<PublicSchedule />} />

          {/* 그 외 주소는 관리자 홈으로 */}
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </main>
    </div>
  );
}
