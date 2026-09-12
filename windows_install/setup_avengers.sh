#!/usr/bin/env bash
# Avengers 윈도우(WSL2) 신규 설치 스크립트
# 사용법: WSL2 Ubuntu 안에서
#   git clone <레포> ~/Avengers
#   bash ~/Avengers/windows_install/setup_avengers.sh
set -e

REPO_DIR="$HOME/Avengers"
DB_NAME="Avengers"
DB_USER="avengers"
DB_PASS="$(openssl rand -hex 12)"
DJANGO_SECRET="$(openssl rand -hex 32)"

echo "[1/9] 시스템 패키지 설치 중... (몇 분 걸릴 수 있습니다)"
sudo apt update
sudo apt install -y git curl wget unzip build-essential openssl \
  python3 python3-venv python3-pip python3-dev pkg-config \
  default-libmysqlclient-dev mysql-server redis-server \
  xvfb x11vnc python3-websockify android-tools-adb

echo "[2/9] Node.js 20 설치 중..."
if ! command -v node >/dev/null 2>&1 || [[ "$(node -v)" != v20* ]]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt install -y nodejs
fi

echo "[3/9] Google Chrome 설치 중..."
if ! command -v google-chrome-stable >/dev/null 2>&1; then
  wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  sudo apt install -y /tmp/chrome.deb
  rm -f /tmp/chrome.deb
fi

echo "[4/9] MySQL / Redis 서비스 시작 중..."
sudo service mysql start
sudo service redis-server start

echo "[5/9] MySQL 데이터베이스 생성 중..."
sudo mysql -e "CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4;"
sudo mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';"
sudo mysql -e "GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost'; FLUSH PRIVILEGES;"

echo "[6/9] .env 파일 생성 중..."
if [ -f "$REPO_DIR/.env" ]; then
  echo "  기존 .env 발견 — 덮어쓰지 않고 .env.new로 저장합니다. 필요하면 직접 비교 후 교체하세요."
  ENV_TARGET="$REPO_DIR/.env.new"
else
  ENV_TARGET="$REPO_DIR/.env"
fi
cat > "$ENV_TARGET" <<EOF
# Server
SERVER_PASSWORD=changeme

# MySQL Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASS}

# Django
DJANGO_SECRET_KEY=${DJANGO_SECRET}
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,*
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Anthropic (AI 기능 쓰려면 발급받아서 채워넣기)
ANTHROPIC_API_KEY=

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_CHANNEL=sms:new
EOF

echo "[7/9] 파이썬 가상환경 + 패키지 설치 중... (시간 좀 걸립니다)"
cd "$REPO_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r "$REPO_DIR/windows_install/requirements-full.txt" -q
deactivate

echo "[8/9] DB 마이그레이션 + 관리자 계정 생성 중..."
cd "$REPO_DIR/backend"
source venv/bin/activate
python manage.py migrate
python manage.py shell -c "
from django.contrib.auth import get_user_model
U = get_user_model()
if not U.objects.filter(username='admin').exists():
    U.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('admin 계정 생성 완료')
else:
    print('admin 계정 이미 있음 — 건너뜀')
"
deactivate

echo "[9/9] 프론트엔드 빌드 + PM2 실행 중..."
cd "$REPO_DIR/frontend"
npm install --silent
npx vite build

sudo npm install -g pm2 --silent

cd "$REPO_DIR"
pm2 start windows_install/ecosystem.windows.config.cjs
pm2 save

WSL_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "======================================================"
echo " 설치 완료!"
echo " 윈도우 브라우저에서 아래 주소로 접속하세요:"
echo "   http://localhost:5173"
echo " 로그인: admin / admin123  (로그인 후 꼭 비밀번호를 바꾸세요)"
echo ""
echo " 이 우분투(WSL) 안쪽 IP: ${WSL_IP} (참고용, 평소엔 몰라도 됨)"
echo "======================================================"
