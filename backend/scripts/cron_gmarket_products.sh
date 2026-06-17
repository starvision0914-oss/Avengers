#!/bin/bash
# 지마켓/옥션 ESM '나의 상품' 수집(GmarketMyProduct) — 상품수·판매상태(비고) 신선도 유지.
# 공유ESM 서브계정은 마스터 크롤이 siteSellerId로 함께 수집하므로 마스터만 돌면 됨(크롤러가 서브 자동 스킵).
# 다른 지마켓 수집(gmkt_*/크롬) 실행 중이면 스킵(중복/크롬충돌 방지).
cd /home/rejoice888/Avengers/backend

# [1회성] 2026-06-16 한정: 상품수집(스킵/완료 무관) 직후 dlwodb000 그룹 상태반영 분석 → 텔레그램.
# 실행되면 이후 이 블록은 무효(날짜 불일치)이므로 제거해도 됨.
oneshot_0616() {
    if [ "$(date +%F)" = "2026-06-16" ]; then
        /usr/bin/python3 manage.py notify_gmkt_group_analysis --eid dlwodb000 >> /tmp/cron_gmkt_oneshot_0616.log 2>&1
    fi
}

if pgrep -f 'import crawlers.gmkt_|crawl_gmarket' >/dev/null 2>&1; then
    echo "$(date '+%F %T') 지마켓 수집 실행중 — 스킵" >> /tmp/cron_gmkt_products.log
    oneshot_0616
    exit 0
fi
echo "$(date '+%F %T') 지마켓 상품수집 시작" >> /tmp/cron_gmkt_products.log
python3 manage.py crawl_gmarket_products >> /tmp/cron_gmkt_products.log 2>&1
echo "$(date '+%F %T') 지마켓 상품수집 완료" >> /tmp/cron_gmkt_products.log
oneshot_0616
