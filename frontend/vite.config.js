import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target:
          "http://k0tjsdj7cj.execute-api.us-east-1.localhost.localstack.cloud:4566",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, "/dev"),
      },
    },
  },
});