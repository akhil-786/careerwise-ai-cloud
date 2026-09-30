import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import process from "node:process";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const endpoint = env.VITE_LOCALSTACK_ENDPOINT || "http://localhost:4566";
  const apiId = env.VITE_LOCALSTACK_API_ID || "k0tjsdj7cj";
  const stage = env.VITE_LOCALSTACK_STAGE || "dev";

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api": {
          target: endpoint,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, `/_aws/execute-api/${apiId}/${stage}`),
        },
      },
    },
  };
});
