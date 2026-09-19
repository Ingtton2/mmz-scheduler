// 사장님용 관리자 홈. 스펙 6.1 의 메뉴들이 여기서 연결됩니다.
import { Link } from "react-router-dom";

// to 가 있으면 동작하는 메뉴, step 만 있으면 아직 준비 중인 메뉴.
const MENU = [
  { key: "staff", label: "직원 관리", desc: "등록 · 정보 수정 · 삭제", to: "/admin/staff" },
  {
    key: "leave",
    label: "연차 관리",
    desc: "연차 부여 · 사용 현황 · 사전휴무 승인",
    to: "/admin/leave",
  },
  {
    key: "staffing",
    label: "근무인원수 설정",
    desc: "포지션×시간대 기준 · 공휴일 관리",
    to: "/admin/staffing",
  },
  {
    key: "schedule",
    label: "근무표 관리",
    desc: "자동배치 · 수동수정 · 직원공개",
    to: "/admin/schedule",
  },
  {
    key: "accounts",
    label: "계정 관리",
    desc: "가입 승인 · PIN 초기화",
    to: "/admin/accounts",
  },
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
                <div className="mt-1 text-xs text-gray-400">{m.desc} →</div>
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
