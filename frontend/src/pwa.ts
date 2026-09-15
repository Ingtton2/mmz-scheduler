// PWA 설정: 서비스워커 등록 + 화면(관리자용/직원용/공개)에 맞는
// manifest·홈화면 아이콘을 그때그때 바꿔 단다.
//
// manifest 는 파일 하나(static)라 index.html 에 고정으로 박아두면 관리자/직원
// 아이콘을 나눌 수 없다. 대신 라우트가 바뀔 때마다 <link rel="manifest">/
// <link rel="apple-touch-icon"> 을 JS로 다시 지정한다 — "홈 화면에 추가"는
// 사용자가 페이지를 연 다음(=JS 실행된 다음) 하는 동작이라 이 방식으로 충분하다
// (카카오톡 미리보기처럼 크롤러가 크롤링하는 경우와 달리 문제없음).

const ADMIN_MANIFEST = "/manifest-admin.webmanifest";
const STAFF_MANIFEST = "/manifest-staff.webmanifest";
const ADMIN_ICON = "/icons/admin-180.png";
const STAFF_ICON = "/icons/staff-180.png";
const ADMIN_THEME_COLOR = "#9C6B23";
const STAFF_THEME_COLOR = "#B08968";

type Persona = "admin" | "staff";

function classify(pathname: string): Persona {
  if (pathname === "/join" || pathname === "/staff-login" || pathname.startsWith("/me")) {
    return "staff";
  }
  return "admin"; // /admin/*, /login, 그 외 전부
}

function setOrRemoveLink(rel: string, href: string | null) {
  const existing = document.head.querySelector<HTMLLinkElement>(`link[rel="${rel}"]`);
  if (href === null) {
    existing?.remove();
    return;
  }
  const el = existing ?? document.createElement("link");
  el.rel = rel;
  el.href = href;
  if (!existing) document.head.appendChild(el);
}

export function syncPwaIdentity(pathname: string) {
  const themeColorEl = document.head.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
  if (classify(pathname) === "staff") {
    setOrRemoveLink("manifest", STAFF_MANIFEST);
    setOrRemoveLink("apple-touch-icon", STAFF_ICON);
    if (themeColorEl) themeColorEl.content = STAFF_THEME_COLOR;
  } else {
    setOrRemoveLink("manifest", ADMIN_MANIFEST);
    setOrRemoveLink("apple-touch-icon", ADMIN_ICON);
    if (themeColorEl) themeColorEl.content = ADMIN_THEME_COLOR;
  }
}

export function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* 서비스워커 등록 실패해도 앱 사용엔 지장 없음 (오프라인 캐시만 못 씀) */
    });
  });
}
