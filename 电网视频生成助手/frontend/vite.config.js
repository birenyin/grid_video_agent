import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/web/",
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/projects": "http://127.0.0.1:8000",
      "/automation": "http://127.0.0.1:8000",
      "/runtime": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000"
    }
  },
  build: {
    outDir: "../app/web/dist",
    emptyOutDir: true
  }
});
