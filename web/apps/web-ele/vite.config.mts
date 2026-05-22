import { defineConfig } from '@vben/vite-config';

import ElementPlus from 'unplugin-element-plus/vite';

export default defineConfig(async () => {
  return {
    application: {},
    vite: {
      plugins: [
        ElementPlus({
          format: 'esm',
        }),
      ],
      server: {
        proxy: {
          '/basic-api': {
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/basic-api/, ''),
            // 本地开发统一转到修复后的后端
            target: 'http://localhost:8002',
            ws: true,
          },
          '/focusaudit-app': {
            changeOrigin: true,
            target: 'http://localhost:5174',
            ws: true,
          },
          '/deepaudit-app': {
            changeOrigin: true,
            target: 'http://localhost:5174',
            ws: true,
          },
        },
      },
    },
  };
});
