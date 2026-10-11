/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LWM_API_BASE?: string;
  readonly VITE_LWM_USE_MOCK?: string;
  readonly VITE_LWM_PROJECT_PATH?: string;
  readonly VITE_LWM_TOOL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
