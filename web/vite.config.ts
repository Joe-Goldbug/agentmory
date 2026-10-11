import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 网关地址：默认走同源代理 /api -> 127.0.0.1:8766
const API_TARGET = process.env.LWM_GATEWAY_TARGET ?? 'http://127.0.0.1:8766';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // 规避 CORS：BaseHTTPRequestHandler 不带任何 CORS 响应头，浏览器直连必被拦截
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
});
