// /me/* 화면 공통 상단 내비게이션 (현재 위치 + 로그아웃).
import { Link, useNavigate } from "react-router-dom";
import { clearStaffToken } from "../../api/meClient";

export default function MeNav({ current }: { current: string }) {
  const navigate = useNavigate();

  function onLogout() {
    clearStaffToken();
    navigate("/staff-login", { replace: true });
  }

  return (
    <div className="mb-4 flex items-center justify-between text-sm">
      <div className="flex items-center gap-2 text-gray-500">
        <Link to="/me" className="hover:underline">
          내 화면
        </Link>
        <span>/</span>
        <span className="text-gray-800">{current}</span>
      </div>
      <button onClick={onLogout} className="text-gray-500 hover:underline">
        로그아웃
      </button>
    </div>
  );
}
