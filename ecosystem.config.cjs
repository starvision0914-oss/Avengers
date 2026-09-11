module.exports = {
  apps: [
    {
      name: 'avengers-backend',
      cwd: '/home/rejoice888/Avengers/backend',
      script: 'manage.py',
      // --noreload: 업로드(수초) 처리 중 코드/파일 변경 시 dev서버 자동리로드가
      // 연결을 끊어 'Network Error'가 나던 문제 차단. 코드 수정 후엔 pm2 restart 필요.
      args: 'runserver 0.0.0.0:8010 --noreload',
      interpreter: '/usr/bin/python3',
      env: {
        PYTHONPATH: '/home/rejoice888/.local/lib/python3.12/site-packages',
        NAVER_CLIENT_ID: 'ZB7fEbSJwUrWryyYoUl_',
        NAVER_CLIENT_SECRET: '841MnNgeuY',
      },
    },
    {
      name: 'avengers-frontend',
      cwd: '/home/rejoice888/Avengers/frontend',
      // 2026-09-11: dev 서버(수백개 미번들 모듈 개별요청)가 서버 과부하 시 체감 로딩을 크게
      // 늦춰서, 프로덕션 빌드(dist/)를 vite preview로 서빙하도록 전환(사용자 선택).
      // 코드 수정 후엔 `cd frontend && npx vite build && pm2 restart avengers-frontend`
      // (또는 scripts/rebuild_frontend.sh) 필요 — dev 모드처럼 저장 즉시 반영되지 않음.
      script: 'node_modules/.bin/vite',
      args: 'preview --host 0.0.0.0 --port 5173',
    },
    {
      name: 'avengers-sms-poller',
      cwd: '/home/rejoice888/Avengers/backend',
      script: 'manage.py',
      args: 'sms_adb_poller --interval 5',
      interpreter: '/usr/bin/python3',
      autorestart: true,
      restart_delay: 3000,
      env: {
        PYTHONPATH: '/home/rejoice888/.local/lib/python3.12/site-packages',
      },
    },
    {
      name: 'avengers-telegram-bot',
      cwd: '/home/rejoice888/Avengers/backend',
      script: 'manage.py',
      args: 'telegram_command_bot --interval 2',
      interpreter: '/usr/bin/python3',
      autorestart: true,
      restart_delay: 3000,
      env: {
        PYTHONPATH: '/home/rejoice888/.local/lib/python3.12/site-packages',
      },
    },
    {
      name: 'avengers-xvfb-vnc',
      script: '/usr/bin/Xvfb',
      args: ':99 -screen 0 1920x1080x24',
      autorestart: true,
      restart_delay: 2000,
    },
    {
      name: 'avengers-x11vnc',
      script: '/usr/bin/x11vnc',
      args: '-display :99 -rfbport 5905 -forever -shared -noxdamage -nopw',
      autorestart: true,
      restart_delay: 3000,
    },
    {
      name: 'avengers-vnc-ws',
      script: '/usr/bin/websockify',
      args: '127.0.0.1:6905 127.0.0.1:5905',
      interpreter: 'none',
      autorestart: true,
      restart_delay: 3000,
    },
  ],
};
