import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Vite 설정. 개발 서버는 http://localhost:5173 에서 돎.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      // index.html 외에 staff-login.html 도 진입점으로 빌드 -> 카카오톡 등에
      // /staff-login 링크를 공유했을 때 index.html 과 다른 제목/설명(OG 태그)이
      // 뜨게 하기 위함. (vercel.json 이 "/staff-login" 요청을 이 파일로 돌려줌)
      input: {
        main: resolve(__dirname, "index.html"),
        "staff-login": resolve(__dirname, "staff-login.html"),
      },
    },
  },
  server: {
    port: 5173,
    // "/api" 로 시작하는 요청은 백엔드(8000)로 전달 -> 브라우저 보안 문제 회피
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
