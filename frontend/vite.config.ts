import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8010',
        changeOrigin: true,
        timeout: 600000,        // 업로드 처리(수초~수십초) 동안 프록시가 끊지 않게
        proxyTimeout: 600000,
        configure: (proxy) => {
          proxy.on('error', (err, _req, res) => {
            console.error('[proxy error]', err.code || err.message)
            try { (res as any).writeHead?.(502, { 'Content-Type': 'application/json' }) } catch { /* noop */ }
            try { (res as any).end?.(JSON.stringify({ error: '백엔드 연결 실패(프록시): ' + (err.code || err.message) })) } catch { /* noop */ }
          })
        },
      },
    },
  },
})
