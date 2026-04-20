import path from "node:path";

import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const legacyBaseRedirectPlugin = {
    name: "legacy-deepaudit-base-redirect",
    configureServer(server: import("vite").ViteDevServer) {
      server.middlewares.use((req, res, next) => {
        const url = req.url || "";
        if (!url.startsWith("/deepaudit-app")) {
          next();
          return;
        }

        const redirectedUrl = url.replace(
          /^\/deepaudit-app(?=\/|$)/,
          "/focusaudit-app",
        );
        res.statusCode = 302;
        res.setHeader("Location", redirectedUrl);
        res.end();
      });
    },
  };

  return {
    base: "/focusaudit-app/",
    plugins: [
      react(),
      legacyBaseRedirectPlugin,
      svgr({
        svgrOptions: {
          icon: true,
          exportType: "named",
          namedExport: "ReactComponent",
        },
      }),
    ],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ["react", "react-dom", "react-router-dom"],
            ui: [
              "@radix-ui/react-dialog",
              "@radix-ui/react-select",
              "@radix-ui/react-tabs",
              "@radix-ui/react-progress",
            ],
            charts: ["recharts"],
            ai: ["@google/generative-ai"],
            utils: ["clsx", "tailwind-merge", "date-fns", "sonner"],
          },
        },
      },
      chunkSizeWarningLimit: 1000,
      sourcemap: false,
      minify: "terser",
      terserOptions: {
        compress: {
          drop_console: true,
          drop_debugger: true,
        },
      },
    },
    server: {
      port: 5174,
      host: true,
      open: "/focusaudit-app/",
      cors: {
        origin: true,
        credentials: true,
        methods: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allowedHeaders: [
          "Authorization",
          "Content-Type",
          "X-DashScope-SSE",
          "X-Requested-With",
        ],
      },
      proxy: {
        "/basic-api": {
          target: env.VITE_API_TARGET || "http://127.0.0.1:8001",
          changeOrigin: true,
          rewrite: (apiPath) => apiPath.replace(/^\/basic-api/, ""),
          secure: false,
          ws: true,
        },
        "/dashscope-proxy": {
          target: "https://dashscope.aliyuncs.com",
          changeOrigin: true,
          secure: true,
          rewrite: (apiPath) => apiPath.replace(/^\/dashscope-proxy/, ""),
          configure: (proxy) => {
            proxy.on("proxyReq", (proxyReq) => {
              proxyReq.setHeader("origin", "https://dashscope.aliyuncs.com");
            });
          },
        },
      },
    },
    preview: {
      port: 4174,
      host: true,
    },
    optimizeDeps: {
      include: [
        "react",
        "react-dom",
        "react-router-dom",
        "@google/generative-ai",
        "recharts",
        "sonner",
      ],
    },
  };
});
