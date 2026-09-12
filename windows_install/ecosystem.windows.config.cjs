// 윈도우(WSL2) 설치용 PM2 설정
// 원본 서버의 ecosystem.config.cjs에서 SMS수신/텔레그램봇(폰 연결 필요)은 제외한 최소 구성.
// 나중에 폰을 연결하면 avengers-sms-poller / avengers-telegram-bot을 추가하면 됨.
const HOME = process.env.HOME;

module.exports = {
  apps: [
    {
      name: 'avengers-backend',
      cwd: `${HOME}/Avengers/backend`,
      script: `${HOME}/Avengers/backend/venv/bin/gunicorn`,
      args: 'config.wsgi:application --bind 0.0.0.0:8010 --workers 2 --timeout 180',
      interpreter: 'none',
    },
    {
      name: 'avengers-frontend',
      cwd: `${HOME}/Avengers/frontend`,
      script: 'node_modules/.bin/vite',
      args: 'preview --host 0.0.0.0 --port 5173',
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
