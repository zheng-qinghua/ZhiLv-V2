import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// /api 开头的请求代理到复现后端(8080),避免跨域、登录 token 也在同源下携带。
export default defineConfig({
  plugins: [vue()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
    },
  },
});
