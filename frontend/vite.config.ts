import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Vite 설정. 개발 서버는 http://localhost:5173 에서 돎.
export default defineConfig({
  plugins: [react(), tailwindcss()],
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
