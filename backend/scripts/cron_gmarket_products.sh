#!/bin/bash
# 지마켓/옥션 ESM '나의 상품' 수집(GmarketMyProduct) — 상품수·판매상태(비고) 신선도 유지.
# 공유ESM 서브계정은 마스터 크롤이 siteSellerId로 함께 수집하므로 마스터만 돌면 됨(크롤러가 서브 자동 스킵).
# 상품수집(www.esmplus.com)은 광고센터(ad.esmplus.com) 크롤들과 별도 세션이라 동시 진행 가능하도록
# 전용 락(gmarket_product)으로 분리함(2026-07-09) — 여기서 다른 지마켓(광고센터) 크롤과 겹친다고
# 셸에서 미리 스킵하지 않는다. 중복 실행 방지는 crawl_gmarket_products 내부 guard.preflight가 처리.
cd /home/rejoice888/Avengers/backend

# [1회성] 2026-06-16 한정: 상품수집(스킵/완료 무관) 직후 dlwodb000 그룹 상태반영 분석 → 텔레그램.
# 실행되면 이후 이 블록은 무효(날짜 불일치)이므로 제거해도 됨.
oneshot_0616() {
    if [ "$(date +%F)" = "2026-06-16" ]; then
        /usr/bin/python3 manage.py notify_gmkt_group_analysis --eid dlwodb000 >> /tmp/cron_gmkt_oneshot_0616.log 2>&1
    fi
}

echo "$(date '+%F %T') 지마켓 상품수집 시작" >> /tmp/cron_gmkt_products.log
python3 manage.py crawl_gmarket_products >> /tmp/cron_gmkt_products.log 2>&1
echo "$(date '+%F %T') 지마켓 상품수집 완료" >> /tmp/cron_gmkt_products.log
oneshot_0616
