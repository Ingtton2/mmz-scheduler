// memeal.zip 서비스 워커 — standalone(홈 화면 설치) 실행 + 오프라인 폴백.
//
// 캐시 갱신 전략:
//  - /api/* 는 절대 캐시하지 않는다 — 스케줄 임시/공유 상태처럼 실시간으로
//    바뀌는 값이 캐시되면 "공유를 취소했는데 직원 화면엔 계속 보임" 같은
//    사고가 난다. 항상 네트워크로 그대로 흘려보낸다.
//  - 페이지 이동(HTML)은 항상 네트워크를 먼저 시도 -> 새로 배포된 버전이 바로 반영됨.
//    (네트워크 실패 시에만 캐시로 폴백 — 오프라인 대비)
//  - JS/CSS/이미지 등 정적 자산은 캐시를 먼저 보여주고 백그라운드로 최신본을 받아
//    다음 번 방문 때 반영 (stale-while-revalidate). Vite 가 빌드마다 파일명에
//    해시를 붙이므로, 내용이 바뀌면 파일명도 바뀌어 예전 캐시와 절대 안 섞인다.
//  - skipWaiting + clients.claim: 새 버전이 배포되면 탭을 안 닫아도 바로 활성화.
const CACHE_NAME = "memealzip-v2";

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // 다른 출처(API 서버 등)는 서비스워커가 손대지 않고 그대로 흘려보낸다.
  if (url.origin !== self.location.origin) return;

  // /api/* 는 같은 출처로 프록시되는 백엔드 요청이라도 절대 캐시하지 않는다.
  if (url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match(request).then((r) => r || caches.match("/"))),
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE_NAME).then((c) => c.put(request, copy));
          }
          return res;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});
