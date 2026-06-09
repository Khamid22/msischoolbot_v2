import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(() => ({
  base: "/static/react/",
  server: {
    host: "::",
    port: 8080,
    hmr: {
      overlay: false,
    },
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    dedupe: ["react", "react-dom", "react/jsx-runtime", "react/jsx-dev-runtime", "@tanstack/react-query", "@tanstack/query-core"],
  },
  build: {
    // Outputs to web/backend/static/react/ — served by Flask
    outDir: "../backend/static/react",
    emptyOutDir: true,
    manifest: "manifest.json",
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        // Add content hash so browsers can cache chunks indefinitely.
        // The hash changes only when the chunk content changes.
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
        // Reduce request fan-out on high-latency/mobile networks by grouping
        // many tiny node_modules chunks into a few stable vendor chunks.
        manualChunks: (id) => {
          if (!id.includes("node_modules")) {
            return undefined;
          }
          if (id.includes("/recharts/")) {
            return "recharts";
          }
          if (id.includes("/lucide-react/")) {
            return "icons";
          }
          if (
            id.includes("/react/") ||
            id.includes("/react-dom/") ||
            id.includes("/scheduler/")
          ) {
            return "react-vendor";
          }
          return "vendor";
        },
      },
    },
  },
}));
