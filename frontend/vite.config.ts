import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  envDir: mode === "validation" || mode === "production" ? false : undefined,
  plugins: [react()],
}));
