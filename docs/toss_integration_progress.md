# 토스몰 광고비 대시보드 — 완료

## 1. 광고비 집계 — 완료
- [x] 로그인 확인 (starvis7942@gmail.com, 2FA 없음, 계정 그대로 사용)
- [x] 크롤러 작성 (crawlers/toss_crawler.py)
- [x] DB 모델 (TossAccount, TossAdCost, TossCampaignAdCost)
- [x] 실데이터 검증: 어제 8,483원/462.15%, 오늘(부분) 4,319원/495.11% — 사이트 값과 정확히 일치
- [x] 크론 등록 (매일 08:00 전일 확정치, cron_toss_adcost.sh)
- [x] 전역락 platform='toss' 신설 — 다른 플랫폼과 동시 실행 가능

## 2. 대시보드 작성 — 완료
- [x] 백엔드 API (/api/toss/accounts/, /dashboard/, /campaigns/)
- [x] 프론트엔드: `/smartstore` 페이지 PLATFORM_TABS에 '토스' 탭 추가
- [x] TossDashboard.tsx — 오늘/어제/이번달(월별)/일자별 버튼 + 캠페인별 전체내역 테이블
- [x] 브라우저 실화면 확인 완료 (로그인 → /smartstore → 토스 탭 → 값 일치 확인)

## 알아둘 점
- 유효광고수익률(ROAS)은 단순 비율(전환거래액/광고비)과 다름 — 단일 날짜는 사이트 카드값을 그대로 저장해 정확,
  여러 날짜를 합친 기간(월별 등)은 근사치(비율)로 표시됨(토스가 가중공식 비공개)
- 광고센터 별도 로그인 없음 — 토스 계정 그대로 사용
