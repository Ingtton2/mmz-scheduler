// 사장님용 관리자 홈. 스펙 6.1 의 메뉴들이 여기서 연결됩니다.
import { Link } from "react-router-dom";

// to 가 있으면 동작하는 메뉴, step 만 있으면 아직 준비 중인 메뉴.
const MENU = [
  { key: "staff", label: "직원 등록/관리", to: "/admin/staff" },
  { key: "leave", label: "연차 관리", to: "/admin/leave" },
  { key: "staffing", label: "필요 인원 설정 (포지션×시간대)", to: "/admin/staffing" },
  { key: "schedule", label: "자동배치 · 수동 수정 · 직원 공개", to: "/admin/schedule" },
  { key: "accounts", label: "직원 계정 승인/PIN 관리", to: "/admin/accounts" },
  { key: "work-codes", label: "근무 코드 설정", step: "다음 단계" },
];

export default function AdminHome() {
  return (
    <div>
      <h1 className="mb-1 text-xl font-bold">memeal.zip 관리자 홈</h1>
      <p className="mb-6 text-sm text-gray-500">
        메뉴를 눌러 각 기능으로 이동합니다.
      </p>

      <ul className="grid gap-3 sm:grid-cols-2">
        {MENU.map((m) =>
          m.to ? (
            <li key={m.key}>
              <Link
                to={m.to}
                className="block rounded-lg border bg-white p-4 transition hover:border-gray-400 hover:shadow-sm"
              >
                <div className="font-semibold">{m.label}</div>
                <div className="mt-1 text-xs text-gray-400">바로 가기 →</div>
              </Link>
            </li>
          ) : (
            <li
              key={m.key}
              className="rounded-lg border bg-white p-4 opacity-50"
            >
              <div className="font-semibold">{m.label}</div>
              <div className="mt-1 text-xs text-gray-400">{m.step}에서 구현 예정</div>
            </li>
          ),
        )}
      </ul>
    </div>
  );
}
