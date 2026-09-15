// 직원용 로그인/가입 신청 화면 공통 뼈대 — 크림 배경 + 상단 독립 로고 + 중앙 정렬.
import { useEffect, type ReactNode } from "react";
import logo from "../assets/new_logo_square.png";

const PAGE_BG = "#F9F3E7";

export default function StaffAuthLayout({ children }: { children: ReactNode }) {
  // iOS Safari 는 화면을 아래로 당겨 튕기는 오버스크롤 때 body 배경색이 드러난다
  // (position: fixed 요소로는 못 가림) — 이 화면에 있는 동안 body 배경을 페이지
  // 배경과 맞춰서 그 순간에도 이어지게 한다.
  useEffect(() => {
    const prevBg = document.body.style.backgroundColor;
    document.body.style.backgroundColor = PAGE_BG;
    return () => {
      document.body.style.backgroundColor = prevBg;
    };
  }, []);

  return (
    <div>
      <div className="fixed inset-0" style={{ backgroundColor: PAGE_BG }} />
      <div className="relative z-10 flex min-h-[calc(100dvh-2rem)] flex-col items-center justify-center gap-6 px-4">
        <img src={logo} alt="memeal.zip" className="h-44 w-44 object-contain" />
        {children}
      </div>
    </div>
  );
}
