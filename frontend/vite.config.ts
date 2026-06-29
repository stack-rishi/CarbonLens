import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    host: true,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'charts': ['recharts'],
          'flow': ['@xyflow/react'],
          'ui': ['@radix-ui/react-dialog', '@radix-ui/react-tabs'],
          'icons': ['lucide-react'],
          'utils': ['date-fns', 'axios']
        }
      }
    },
    chunkSizeWarningLimit: 600,
    minify: 'esbuild',
    target: 'es2020'
  }
});
