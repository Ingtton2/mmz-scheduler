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
import LeaveManagementPage from "./pages/LeaveManagementPage";
import StaffingPage from "./pages/StaffingPage";
import SchedulePage from "./pages/SchedulePage";
import StaffAccountsPage from "./pages/StaffAccountsPage";
import LoginPage from "./pages/LoginPage";
import JoinPage from "./pages/JoinPage";
import StaffLoginPage from "./pages/StaffLoginPage";
import MyHome from "./pages/me/MyHome";
import MyPinChangePage from "./pages/me/MyPinChangePage";
import MyLeavePage from "./pages/me/MyLeavePage";
import MyDayOffPage from "./pages/me/MyDayOffPage";
import MySchedulePage from "./pages/me/MySchedulePage";
import MyTeamSchedulePage from "./pages/me/MyTeamSchedulePage";
import RequireAuth from "./RequireAuth";
import RequireStaffAuth from "./RequireStaffAuth";
import { getAuthStatus, logout as apiLogout } from "./api/auth";
import logo from "./assets/logo.png";
import { clearToken, getToken } from "./api/client";
import { syncPwaIdentity } from "./pwa";

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

// 이 화면들은 각자 자기만의 헤더(또는 무헤더)를 쓰므로, 관리자 공통 헤더를 숨긴다.
const NO_ADMIN_CHROME_PREFIXES = ["/schedule/", "/join", "/staff-login", "/me"];

export default function App() {
  const location = useLocation();
  const isAdminChrome = !NO_ADMIN_CHROME_PREFIXES.some((p) => location.pathname.startsWith(p));

  // 화면(관리자용/직원용/공개)이 바뀔 때마다 PWA 매니페스트·홈화면 아이콘을 맞춰 단다.
  useEffect(() => {
    syncPwaIdentity(location.pathname);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-cream text-ink">
      {isAdminChrome && (
        <header className="flex items-center justify-between border-b bg-white px-4 py-3">
          <Link to="/admin" className="flex items-center gap-2 font-bold">
            <img src={logo} alt="" className="h-7 w-7 rounded" />
            memeal.zip
          </Link>
          <LogoutButton />
        </header>
      )}

      <main className="mx-auto max-w-6xl p-4">
        <Routes>
          {/* 관리자 로그인 (스펙 1단계) */}
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
                <LeaveManagementPage />
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
          <Route
            path="/admin/accounts"
            element={
              <RequireAuth>
                <StaffAccountsPage />
              </RequireAuth>
            }
          />

          {/* 직원 셀프서비스 — 스펙 9 */}
          <Route path="/join" element={<JoinPage />} />
          <Route path="/staff-login" element={<StaffLoginPage />} />
          <Route
            path="/me"
            element={
              <RequireStaffAuth>
                <MyHome />
              </RequireStaffAuth>
            }
          />
          <Route
            path="/me/change-pin"
            element={
              <RequireStaffAuth>
                <MyPinChangePage />
              </RequireStaffAuth>
            }
          />
          <Route
            path="/me/leave"
            element={
              <RequireStaffAuth>
                <MyLeavePage />
              </RequireStaffAuth>
            }
          />
          <Route
            path="/me/dayoff"
            element={
              <RequireStaffAuth>
                <MyDayOffPage />
              </RequireStaffAuth>
            }
          />
          <Route
            path="/me/schedule"
            element={
              <RequireStaffAuth>
                <MySchedulePage />
              </RequireStaffAuth>
            }
          />
          <Route
            path="/me/team-schedule"
            element={
              <RequireStaffAuth>
                <MyTeamSchedulePage />
              </RequireStaffAuth>
            }
          />

          {/* 그 외 주소는 관리자 홈으로 */}
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </main>
    </div>
  );
}
