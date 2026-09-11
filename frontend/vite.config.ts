import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// server(dev)와 preview(프로덕션 빌드 서빙)가 동일한 프록시를 쓰도록 공유
// (2026-09-11: 서버 과부하로 인한 /owner 로딩지연 대응 — dev 모드는 수백 개 미번들 모듈을
// 낱개 요청하느라 느려서, 평소엔 빌드된 프로덕션 산출물을 vite preview로 서빙한다).
const proxyConfig = {
  '/api': {
    target: 'http://localhost:8010',
    changeOrigin: true,
    timeout: 600000,        // 업로드 처리(수초~수십초) 동안 프록시가 끊지 않게
    proxyTimeout: 600000,
    configure: (proxy: any) => {
      proxy.on('error', (err: any, _req: any, res: any) => {
        console.error('[proxy error]', err.code || err.message)
        try { res.writeHead?.(502, { 'Content-Type': 'application/json' }) } catch { /* noop */ }
        try { res.end?.(JSON.stringify({ error: '백엔드 연결 실패(프록시): ' + (err.code || err.message) })) } catch { /* noop */ }
      })
    },
  },
  '/vnc-ws': {
    target: 'ws://127.0.0.1:6905',
    ws: true,
  },
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: proxyConfig,
  },
  preview: {
    host: '0.0.0.0',
    port: 5173,
    proxy: proxyConfig,
  },
})
