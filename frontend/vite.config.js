import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";


export default defineConfig(({ mode }) => ({
  base: mode === "production" ? "/static/" : "/",
  plugins: [react()],
  build: {
    outDir: "../backend/staticfiles",
    emptyOutDir: true,
  },
}));
