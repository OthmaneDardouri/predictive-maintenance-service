import { defineConfig } from "vite";

// Dev server only: mirrors the nginx proxy, adding the API key server-side.
// The key is read from the shell environment and never reaches the browser bundle.
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.API_URL ?? "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
        headers: { "X-API-Key": process.env.API_KEY ?? "" },
      },
    },
  },
});
