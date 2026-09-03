# Avengers 시스템 이전 가이드 (서버 → Windows/WSL2)

이 문서는 이 컴퓨터(원본 서버, 192.168.1.16)에만 저장되어 있습니다. 어디에도 게시/업로드하지 않았습니다.
**비밀번호·API키 등 실제 값은 이 문서 어디에도 없습니다.** 아래 "옮겨야 할 파일" 목록에 있는 파일들을
USB나 직접 파일복사로 두 컴퓨터 사이에서만 옮기세요 — 그 값을 저(Claude)에게 보여주거나 채팅에 붙여넣지 않으셔도 됩니다.

작성일: 2026-09-03

---

## 0. 왜 "js 파일 하나"가 아닌가

이 시스템은 파이썬(Django) 백엔드 + 리액트 프론트엔드 + MySQL 데이터베이스 + 브라우저 자동화(Selenium/Chrome)로
이루어져 있습니다. 자바스크립트 파일 하나로 만드는 건 전체를 처음부터 다시 만드는 것과 같아서 하지 않았습니다.
대신 **지금 서버와 똑같은 환경을 새 컴퓨터에 그대로 설치**하는 방식으로 진행합니다.

## 1. 새 컴퓨터 준비 (Windows)

1. **WSL2 설치**: Windows에서 PowerShell을 관리자 권한으로 열고 아래 명령 실행
   ```
   wsl --install -d Ubuntu-24.04
   ```
   재부팅 후 사용자 이름을 물어보면 **반드시 `rejoice888`로 설정**하세요(원본 서버와 동일). 이래야
   `/home/rejoice888/...`로 박혀있는 경로 114곳(스크립트 73개, 파이썬 41개)을 하나도 안 고쳐도 됩니다.
   다른 이름을 쓰면 그 경로들을 전부 찾아 바꿔야 해서 훨씬 번거롭습니다.

2. WSL2 안에서(Ubuntu 터미널) 기본 패키지 업데이트:
   ```
   sudo apt update && sudo apt upgrade -y
   ```

## 2. 새 컴퓨터에 설치할 프로그램들

원본 서버 기준 버전(괄호 안)에 최대한 맞추면 안전합니다.

| 항목 | 원본 서버 버전 | 설치 명령(WSL2 Ubuntu) |
|---|---|---|
| Python | 3.12.3 | `sudo apt install python3.12 python3-pip` |
| Node.js | 20.20.2 | `curl -fsSL https://deb.nodesource.com/setup_20.x \| sudo -E bash - && sudo apt install nodejs` |
| MySQL | 8.0.46 | `sudo apt install mysql-server` |
| Redis | 7.0.15 | `sudo apt install redis-server` |
| Google Chrome | 146.x | `wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && sudo apt install ./google-chrome-stable_current_amd64.deb` |
| Xvfb, x11vnc, websockify (화면없는 브라우저 구동용) | - | `sudo apt install xvfb x11vnc websockify` |
| 한글 폰트 (크롤러 화면인식에 필요) | - | `sudo apt install fonts-nanum fonts-nanum-coding` |
| PM2 (서비스 관리자) | - | `sudo npm install -g pm2` |

chromedriver는 셀레니움이 첫 실행 시 자동으로 받아옵니다(버전 자동 매칭) — 따로 설치할 필요 없습니다.

## 3. 코드 옮기기

가장 깔끔한 방법은 git으로 옮기는 겁니다(지마켓 계정정보 같은 실제 데이터는 git에 없고 코드만 있음):
```
cd /home/rejoice888
git clone https://github.com/starvision0914-oss/Avengers.git
```
(GitHub 로그인 필요하면 원본 서버에서 쓰던 방식 그대로 사용)

`node_modules`와 `.git` 캐시는 git clone하면 자동으로 안 딸려오니 신경 안 쓰셔도 됩니다.
**`backend/media` 폴더(939MB, 업로드된 이미지 등)는 git에 없어서 별도로 복사해야 합니다** — USB나
`scp` 등으로 원본 서버의 `/home/rejoice888/Avengers/backend/media` 전체를 새 컴퓨터의 같은 위치로 복사하세요.

## 4. 옮겨야 할 "비밀 파일들" (내용은 절대 채팅에 붙여넣지 마세요)

아래 파일들은 git에 없고, USB나 직접 파일복사로만 옮겨야 합니다:

- `/home/rejoice888/Avengers/.env` — DB 비밀번호, Django 키, 텔레그램/구글 관련 설정 등
- `/home/rejoice888/Avengers/backend/credentials.json` — 구글 시트 연동용 서비스계정 키
- `/home/rejoice888/Avengers/migration_backup/avengers_db_backup_20260903.sql.gz` — DB 전체 백업(395MB)

**추가로 확인할 것**: `ecosystem.config.cjs` 파일 안에 네이버 API 키(NAVER_CLIENT_ID/SECRET)가
`.env`가 아니라 이 설정파일에 직접 박혀있습니다. 이전하면서 `.env`로 옮기는 걸 권장드립니다(나중에
원하시면 제가 코드를 수정해드릴 수 있습니다) — 지금 당장 필수는 아니고, 이 파일도 git에 안 올라가 있으니
그대로 복사해서 옮기면 우선 작동은 합니다.

## 5. 새 컴퓨터에서 설치 실행

```
cd /home/rejoice888/Avengers/backend
pip install -r requirements.txt
# requirements.txt에 8개만 적혀있어 부족합니다. 아래 파일로 전체 설치하세요.
pip install -r /home/rejoice888/Avengers/migration_backup/pip_freeze_full.txt

cd /home/rejoice888/Avengers/frontend
npm install
```

## 6. 데이터베이스 복원

```
sudo mysql -e "CREATE DATABASE Avengers CHARACTER SET utf8mb4;"
sudo mysql -e "CREATE USER 'rejoice888'@'localhost' IDENTIFIED BY '(.env의 DB_PASSWORD 값)';"
sudo mysql -e "GRANT ALL PRIVILEGES ON Avengers.* TO 'rejoice888'@'localhost';"
gunzip -c /home/rejoice888/Avengers/migration_backup/avengers_db_backup_20260903.sql.gz | mysql -u rejoice888 -p Avengers
```
(마지막 줄은 몇 분 정도 걸릴 수 있습니다 — 9GB 분량입니다)

## 7. 크론(정기작업) 등록

```
sudo apt install cron
sudo service cron start
crontab /home/rejoice888/Avengers/migration_backup/crontab_backup.txt
```

## 8. PM2로 서비스 실행

```
cd /home/rejoice888/Avengers
pm2 start ecosystem.config.cjs
pm2 save
```

## 9. 확인이 필요한 것 (자동으로 안 되는 부분)

- **스마트폰(문자수신용)**: 물리적인 기기라 옮길 수 없습니다. 새 컴퓨터에 USB로 연결해서
  `adb devices`로 인식되는지 확인하고, smsApp을 다시 설정해야 합니다.
- **CORS 허용 목록**: `backend/config/settings.py`의 `CORS_ALLOWED_ORIGINS`에 원본 서버 IP가
  하드코딩되어 있습니다(`192.168.1.16`). WSL2는 보통 `localhost`로 자동 접속되니 문제없을 가능성이
  높지만, 다른 기기(스마트폰 등)에서 새 컴퓨터의 LAN IP로 접속해야 한다면 그 IP를 이 목록에 추가해야 합니다.
- **크론 실행 여부**: WSL2는 컴퓨터를 껐다 켜면 자동으로 안 켜질 수 있습니다(Windows 작업 스케줄러로
  "로그인 시 WSL 자동 시작" 설정을 추가하는 걸 권장 — 필요하시면 제가 설정해드릴 수 있습니다).

## 10. 준비된 백업 파일 위치 (이 컴퓨터 안)

```
/home/rejoice888/Avengers/migration_backup/
├── avengers_db_backup_20260903.sql.gz   (395MB, DB 전체)
├── pip_freeze_full.txt                   (설치된 파이썬 패키지 263개 전체 목록)
├── crontab_backup.txt                    (정기작업 61줄 전체)
└── MIGRATION_GUIDE.md                    (이 문서)
```
