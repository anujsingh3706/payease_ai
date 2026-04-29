// frontend/vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir:       "dist",
    sourcemap:    false,       // No source maps in production
    minify:       "terser",    // Smaller bundle
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // Split vendor chunks for better caching
        manualChunks: {
          vendor:   ["react", "react-dom", "react-router-dom"],
          charts:   ["recharts"],
          ui:       ["lucide-react"],
          query:    ["@tanstack/react-query"],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target:      "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});