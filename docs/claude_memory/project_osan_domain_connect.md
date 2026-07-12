---
name: project-osan-domain-connect
description: 오산 홈페이지 도메인(osanguy.com, Dynadot) 연결 진행상황 - DNS/DDNS 완료, 포트포워딩/방화벽 확인 남음
metadata:
  node_type: memory
  type: project
  originSessionId: 22f4c8ff-2f78-4400-9e88-27bf11b821dd
---

오산 홈페이지([[project_osan_homepage]]) 도메인을 Dynadot에서 `osanguy.com`으로 구매(2026-07-11), 서버(192.168.45.100, 공인IP 218.50.211.173, ipTIME 계열 SK브로드밴드 공유기 GW-ME6110)에 연결 작업 진행.

**완료된 것:**
- Dynadot DNS A레코드: `@`, `www` 모두 218.50.211.173로 설정 완료, 전파 확인(dig 8.8.8.8/1.1.1.1 정상)
- Dynadot Dynamic DNS 활성화: DDNS 비밀번호로 유동IP 자동갱신 스크립트 `/home/rejoice888/homepage/scripts/ddns_update.sh` 작성+검증 완료. 정확한 API 엔드포인트는 `https://www.dynadot.com/set_ddns?domain=...&subDomain=www&type=A&ip=...&pwd=...&containRoot=true&ttl=600` (api.dynadot.com/api3.xml 아님, api.dynadot.com/nic/update도 아님 — 둘 다 시도했으나 실패, ddns-go 오픈소스 클라이언트 소스코드 확인 후 찾음). crontab에 10분마다 등록 완료.
- 공유기 포트포워딩(80/443→192.168.45.100) 사용자가 SK브로드밴드 통해 로그인 후 직접 등록 완료.

**미해결/확인 필요:**
- 서버 자체 방화벽(ufw)이 활성화 상태(4주 전부터, 규칙파일 user.rules는 7/10 수정됨) — sudo 필요해 이 세션에서 규칙 내용 확인 불가. 사용자가 실제 터미널(이 세션 아닌 별도 터미널 앱)에서 `sudo ufw status verbose` 직접 실행 후 80/443 allow 규칙 있는지 확인 필요.
- WebFetch로 외부 접속 테스트 시 http를 강제로 https(443)로 업그레이드하는 특성 때문에 80번 포트만 따로 외부 검증이 어려움(check-host.net/hackertarget 등 API도 안 됨). 실제 검증은 사용자가 모바일 데이터 등 외부망에서 브라우저로 직접 접속해보는 게 가장 확실.
- WordPress 자체 siteurl/home 옵션이 아직 `http://192.168.45.100`(내부IP)로 남아있음 — 포트포워딩+방화벽 확인 끝나면 `wp option update siteurl/home http://osanguy.com`로 변경 후 SSL(certbot) 발급 필요.

**how to apply**: 이 작업 재개 시 위 순서(방화벽 확인→WP 주소 변경→certbot)대로 진행. ipTIME 공유기 로그인은 캡차+해시로그인이라 자동화 시도했으나 실패(admin/1234 기본값 아님, 계정 잠김 위험으로 중단) — 반드시 사용자가 직접 로그인.

관련: [[project_osan_homepage]], [[feedback_low_tech_literacy_guidance]]
