module.exports = {
  apps: [
    {
      // 2026-09-12: manage.py runserver(개발용, 요청 순차처리만 가능)→gunicorn 3워커로 전환.
      // 실측: 동일 API 3개 동시요청이 순서대로 처리돼 시간이 3배로 늘어나던 문제 해결.
      // 코드 수정 후엔 여전히 pm2 restart 필요(reload 안 씀 — 업로드 중 재시작 시 연결끊김 방지,
      // 기존 --noreload와 같은 이유).
      name: 'avengers-backend',
      cwd: '/home/rejoice888/Avengers/backend',
      script: '/home/rejoice888/.local/bin/gunicorn',
      args: 'config.wsgi:application --bind 0.0.0.0:8010 --workers 3 --timeout 180',
      interpreter: 'none',
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
      // 2026-09-17 사용자요청: 도매마트 L코드 품절/미확인 상태를 무한반복으로 계속 재조회
      // (멈추면 안 됨). check_domemart_lcodes --only-status soldout,not_found를
      // while true로 반복 — 한 회차 끝나면(처리할 항목 없음) 바로 다음 회차 재시작.
      name: 'avengers-lcode-soldout-loop',
      cwd: '/home/rejoice888/Avengers/backend',
      script: 'scripts/loop_lcode_soldout_recheck.sh',
      interpreter: 'none',
      autorestart: true,
      restart_delay: 5000,
    },
    {
      // 2026-09-18 사용자요청: 옥션광고센터(ad.esmplus.com) 일반광고 그룹 중 L코드(도매마트)
      // 상품이 있는 그룹만 찾아서 노출요일/시간 전략(기본 월~금 8~16시)을 자동 적용.
      // 계정당 그룹이 수백 개라 30개씩 나눠 무한반복(check_domemart_lcodes와 동일 원칙).
      name: 'avengers-gmarket-ad-strategy-loop',
      cwd: '/home/rejoice888/Avengers/backend',
      script: 'scripts/loop_gmarket_ad_strategy.sh',
      interpreter: 'none',
      autorestart: true,
      restart_delay: 5000,
    },
    {
      // 2026-09-18 사용자요청: tmxkql111/tmxkql222/dlrmsgh012 3계정 전체 그룹의 노출요일/시간을
      // "사용안함"으로 일괄처리(금요일 광고 안 켜지던 문제 긴급대응). 멱등 — 완료 확인되면
      // 사용자가 pm2 stop/delete로 내려주면 됨(자동종료 조건 없음, 계속 재확인만 함).
      name: 'avengers-gmarket-friday-fix-loop',
      cwd: '/home/rejoice888/Avengers/backend',
      script: 'scripts/loop_gmarket_friday_fix.sh',
      interpreter: 'none',
      autorestart: true,
      restart_delay: 5000,
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
