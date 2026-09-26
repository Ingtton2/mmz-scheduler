// 휴가 일정 공유 화면에 있는 동안만 페이지 배경을 이 기능 전용 톤(#F6F1EC / 다크)으로 바꾼다.
import { useEffect } from "react";

export function useVacationTheme() {
  useEffect(() => {
    const el = document.documentElement;
    el.classList.add("vn-active");
    return () => el.classList.remove("vn-active");
  }, []);
}
