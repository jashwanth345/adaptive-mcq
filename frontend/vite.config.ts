import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { localOrigin } from './local-origin.ts';
import { browserHeaders, previewHeaders } from './security-headers.ts';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, import.meta.dirname, 'LOCAL_API_');
  const proxy = { '/api': { target: localOrigin(process.env.LOCAL_API_ORIGIN ?? env.LOCAL_API_ORIGIN), changeOrigin: true } };
  return {
    plugins: [react(), tailwindcss()],
    // React development refresh injects inline code; the built preview has the
    // strict script policy. Neither server permits cross-origin asset reads.
    server: { host: 'localhost', port: 5173, strictPort: true, proxy, cors: false, headers: browserHeaders },
    preview: { host: 'localhost', port: 5173, strictPort: true, proxy, cors: false, headers: previewHeaders },
    test: { environment: 'jsdom', setupFiles: './tests/setup.ts', include: ['tests/**/*.test.{ts,tsx}'], maxWorkers: 1 },
  };
});
