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
      script: 'node_modules/.bin/vite',
      args: '--host 0.0.0.0 --port 5173',
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
  ],
};
