/// <reference types="vite/client" />

interface ImportMetaEnv {
  // 배포 시 백엔드 API 주소를 직접 지정하고 싶을 때만 사용 (보통은 비워둠).
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
