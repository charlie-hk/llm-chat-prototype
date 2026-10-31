import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The frontend talks to the FastAPI backend on :8000.
// In dev we proxy /api so the browser sees a same-origin request.
export default defineConfig({
  plugins: [react()],
  // Relative base so the build works when served from a GitHub Pages subpath.
  base: "./",
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
