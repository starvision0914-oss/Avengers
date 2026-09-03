# Windows 네이티브 이전 — 순서대로 붙여넣을 프롬프트 7개

이 파일은 이 컴퓨터(원본 서버)에만 저장되어 있고 게시하지 않았습니다. 비밀번호/API키 값은 없습니다.

**사용법**: 새 Windows 컴퓨터에서 Claude Code를 실행하고, 아래 프롬프트 1을 그대로 복사해서 붙여넣고
끝날 때까지 기다린 다음, 프롬프트 2로 넘어가세요. 순서를 건너뛰지 마세요(뒤 단계가 앞 단계 결과에 의존합니다).

각 프롬프트 안의 `[여기에 ...]`는 실제 상황에 맞게 채워 넣으세요.

---

## 프롬프트 1 — 환경 조사 및 설치 계획

```
Windows 컴퓨터에 "Avengers"라는 파이썬(Django)+리액트+MySQL 시스템을 새로 설치하려고 해.
원본은 리눅스 서버였는데, 이번엔 Windows에 네이티브로 설치할 거야(WSL 안 씀).

먼저 이 컴퓨터에 뭐가 이미 깔려있는지 조사해줘:
- Python 버전 (3.12 필요)
- Node.js 버전 (20.x 필요)
- MySQL 설치 여부 (8.0 필요)
- Redis 설치 여부 (7.x 필요, 없으면 Windows용 대안 찾아줘 — Redis는 공식 Windows 지원이 약해서
  Memurai 같은 대안이나 WSL 최소설치만 Redis용으로 쓰는 방법도 고려해줘)
- Google Chrome 설치 여부
- Git 설치 여부
- PowerShell 버전

없는 건 설치해줘. 전부 설치 끝나면 각 버전을 다시 확인해서 보고해줘. 아직 코드는 안 옮길 거니까
설치만 진행하고 다음 단계는 기다려줘.
```

---

## 프롬프트 2 — 코드 가져오기 + 파이썬/노드 패키지 설치

```
GitHub에서 Avengers 프로젝트를 가져올 거야: https://github.com/starvision0914-oss/Avengers
[원하는 폴더 경로, 예: C:\Users\[사용자명]\Avengers] 에 클론해줘.

그 다음 backend 폴더에서 파이썬 패키지를 설치해야 하는데, 원본 서버(리눅스)에서 설치돼있던
전체 패키지 목록 파일을 내가 USB로 옮겨놨어. 그 파일 경로는 [옮긴 경로]/pip_freeze_full.txt 야.
이 파일 내용으로 pip install을 진행해줘. 단, 이 목록은 리눅스 기준이라 일부 패키지는
Windows에서 설치가 안 될 수 있어(예: 리눅스 전용 C확장 패키지) — 설치 실패하는 게 있으면
그게 정말 필요한 기능인지 코드에서 확인하고, Windows 대안이 있으면 그걸로 바꾸고,
없으면 나한테 알려줘.

frontend 폴더에서는 npm install 해줘(package.json 기준, 이건 Windows에서도 문제없을 거야).

전부 설치되면 뭐가 성공했고 뭐가 실패했는지, 실패한 건 왜 그런지 보고해줘.
```

---

## 프롬프트 3 — 비밀 파일 배치 + 데이터베이스 복원

```
USB로 옮겨온 파일들을 배치할 거야:
1. .env 파일을 [Avengers 클론 경로]\.env 에 놔줘 (이미 옮겨놨어, 위치 확인만)
2. credentials.json을 [Avengers 클론 경로]\backend\credentials.json 에 놔줘
3. DB 백업파일(avengers_db_backup_*.sql.gz, 395MB)이 [옮긴 경로]에 있어.

MySQL에 Avengers라는 이름으로 새 데이터베이스를 만들고, 이 백업파일을 복원해줘.
gz 압축파일이라 Windows에서 풀어야 할 수도 있어(7-Zip 등 확인). .env 파일 안에 DB 접속정보
(DB_USER, DB_PASSWORD 등)가 있으니 그 값으로 MySQL 계정도 맞춰서 만들어줘. .env 파일 내용은
나한테 다시 보여주지 말고 네가 직접 읽어서 써줘 — 채팅에 비밀번호 출력하지 마.

복원 끝나면 테이블 개수 세서(원본은 122개였음) 맞는지 확인해줘.
```

---

## 프롬프트 4 — 백엔드/프론트엔드 실행 확인

```
Django 백엔드를 Windows에서 실행해줘: backend 폴더에서
python manage.py runserver 0.0.0.0:8010
프론트엔드는 frontend 폴더에서
npm run dev -- --host 0.0.0.0 --port 5173

둘 다 에러 없이 뜨는지 확인하고, 브라우저로 http://localhost:5173 접속해서 로그인 화면이
뜨는지 확인해줘. 에러 나면 (특히 DB 연결, PYTHONPATH 관련) 원인 찾아서 고쳐줘.
```

---

## 프롬프트 5 — 크론(정기작업) 61개를 Windows 작업 스케줄러로 재등록

```
원본 리눅스 서버는 crontab으로 61개의 정기작업(예: "0 9 * * * 지마켓_광고비수집.sh")을 돌렸어.
그 전체 목록 파일이 [옮긴 경로]/crontab_backup.txt 에 있어.

이 각각의 항목을 Windows "작업 스케줄러"(Task Scheduler)에 등록해야 하는데, 원본의 .sh 스크립트들은
backend/scripts/ 폴더에 있고 리눅스 bash 문법으로 되어있어서 Windows에서 못 돌아가.

각 .sh 스크립트를 열어서 내용을 확인하고(대부분 "python manage.py 커맨드이름 --옵션" 형태일 거야),
그 파이썬 명령어를 그대로 실행하는 PowerShell(.ps1) 스크립트로 하나씩 바꿔줘. 그 다음 그 .ps1들을
crontab_backup.txt에 있는 것과 같은 시각에 실행되도록 작업 스케줄러에 등록해줘.

61개면 많으니까, 먼저 스크립트 5개 정도만 변환+등록해서 정상 동작하는지 나한테 확인받고,
괜찮으면 나머지 전부 같은 방식으로 처리해줘.
```

---

## 프롬프트 6 — 브라우저 자동화(크롤러) Windows 방식으로 전환

```
이 프로젝트의 크롤러들(11번가/지마켓/스마트스토어 등 로그인해서 데이터 가져오는 코드)은
crawlers/browser.py 에서 Selenium으로 Chrome을 띄우는데, 원본 리눅스 서버는 Xvfb(가상 화면)+VNC로
화면 없이 돌리고 필요할 때만 원격으로 들여다봤어. Windows엔 Xvfb가 없어.

crawlers/browser.py를 확인해서, Windows에서는 그냥 Chrome을 headless 옵션으로 띄우거나(더 간단함),
또는 화면에 실제로 띄워서 돌리는 방식으로 바꿔줘(Windows는 어차피 화면이 있으니까 안 띄워도
문제없다면 headless가 편함 — 단, 일부 사이트는 headless를 감지해서 차단할 수 있으니 그 부분도
염두에 둬).

바꾼 다음 아무 계정 하나로 실제 로그인 크롤이 되는지 테스트해줘(예: python manage.py
crawl_11st_cost --accounts [테스트계정] --limit 1 같은 식으로 가벼운 것부터).
```

---

## 프롬프트 7 — 상시 서비스 등록 (PM2) + 최종 점검

```
원본 서버는 pm2로 8개 서비스(백엔드, 프론트엔드, 문자수신 폴러, 텔레그램봇 등)를 상시 실행했어.
Xvfb/x11vnc/websockify 3개는 Windows에 해당 기능이 없으니 제외하고, 나머지 5개
(avengers-backend, avengers-frontend, avengers-sms-poller, avengers-telegram-bot)를
Windows에도 npm install -g pm2로 설치해서 등록해줘. ecosystem.config.cjs 파일을 참고하되
Xvfb 관련 3개 항목은 빼줘.

문자수신(sms-poller)은 스마트폰을 이 Windows 컴퓨터에 USB로 연결하고 adb(Android Debug
Bridge)가 인식하는지부터 확인해줘 — adb 자체가 Windows에 없으면 설치 필요.

마지막으로 전체 점검 체크리스트를 만들어서 하나씩 확인해줘:
- [ ] 백엔드/프론트엔드 정상 접속
- [ ] DB 데이터 정상 조회(예: 계정 목록 페이지)
- [ ] 크론 5개 이상 정상 실행 확인
- [ ] 크롤러 1개 이상 실제 로그인 성공
- [ ] 스마트폰 문자수신 연결 확인
- [ ] pm2 서비스 전체 online 상태
```

---

## 참고: 이 순서를 따라가다 막히면

각 프롬프트는 이전 단계가 끝나야 다음이 됩니다. 중간에 에러가 나면 그 자리에서 "이 에러 고쳐줘"라고
바로 얘기하고, 해결되면 다음 프롬프트로 넘어가세요. 전체를 한 번에 다 시키지 말고 이렇게 나눠서
진행하는 게 문제 생겼을 때 원인 찾기가 훨씬 쉽습니다.
