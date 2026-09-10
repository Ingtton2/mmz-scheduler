// 최상위 화면 + 주소(URL)별 화면 분기.
// 스펙 6장의 두 종류 화면을 여기서 나눕니다.
import { Routes, Route, Link, Navigate } from "react-router-dom";
import AdminHome from "./pages/AdminHome";
import StaffPage from "./pages/StaffPage";
import LeavePage from "./pages/LeavePage";
import DayOffPage from "./pages/DayOffPage";
import StaffingPage from "./pages/StaffingPage";
import SchedulePage from "./pages/SchedulePage";
import PublicSchedule from "./pages/PublicSchedule";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b bg-white px-4 py-3">
        <Link to="/admin" className="font-bold">
          mmz-scheduler
        </Link>
      </header>

      <main className="mx-auto max-w-6xl p-4">
        <Routes>
          {/* 사장님용 (관리자) — 스펙 6.1 */}
          <Route path="/admin" element={<AdminHome />} />
          <Route path="/admin/staff" element={<StaffPage />} />
          <Route path="/admin/leave" element={<LeavePage />} />
          <Route path="/admin/dayoff" element={<DayOffPage />} />
          <Route path="/admin/staffing" element={<StaffingPage />} />
          <Route path="/admin/schedule" element={<SchedulePage />} />

          {/* 직원 조회 전용 — QR 로 접속. 로그인 없음 — 스펙 6.2 */}
          <Route path="/schedule/:shareCode" element={<PublicSchedule />} />

          {/* 그 외 주소는 관리자 홈으로 */}
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </main>
    </div>
  );
}
