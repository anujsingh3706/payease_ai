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
        manualChunks(id) {
          if (['react', 'react-dom', 'react-router-dom'].some(pkg => id.includes(`node_modules/${pkg}`))) return 'vendor';
          if (id.includes('node_modules/recharts')) return 'charts';
          if (id.includes('node_modules/lucide-react')) return 'ui';
          if (id.includes('node_modules/@tanstack/react-query')) return 'query';
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});