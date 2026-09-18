#!/bin/bash
# 옥션광고센터 L코드(도매마트) 상품 보유 계정 전체의 일반광고 그룹 노출요일/시간을
# "사용안함"으로 일괄 처리 — 금요일에 광고가 안 켜지던 문제 해결(2026-09-18, 전체 L코드 계정 확대).
# 계정 목록은 매 회차 새로 계산(L코드 상품 보유 계정이 나중에 늘어도 자동 포함).
# 멱등이라 반복 실행해도 안전(이미 처리된 그룹은 빠르게 스킵).
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"

while true; do
    python3 -u manage.py shell -c "
import re
from apps.cpc.models import GmarketMyProduct, CrawlerAccount, protected_login_ids
from crawlers.gmarket_ad_strategy_crawler import run_fix_friday_all_groups

protected = protected_login_ids('gmarket')
# 공유ESM 중복 서브아이디(2026-09-18 사용자 확인) — 마스터 계정이 대신 처리하므로 스킵
_DUP_SUB = {'starvisi', 'rejoice235', 'rejoice236', 'rejoice223', 'rejoice224'}
accs = (CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
        .exclude(login_id__in=protected).exclude(login_id__in=_DUP_SUB))
login_ids = [a.login_id for a in accs
             if GmarketMyProduct.objects.filter(account=a, seller_product_code__istartswith='LCE_').exists()]
# 이미 확인된 급한 3계정을 앞으로 정렬(먼저 처리)
priority = ['tmxkql111', 'tmxkql222', 'dlrmsgh012']
login_ids.sort(key=lambda x: (x not in priority, priority.index(x) if x in priority else 0))
print(f'L코드 계정 {len(login_ids)}개 대상: {login_ids}')
for lid in login_ids:
    res = run_fix_friday_all_groups(lid, log_fn=print)
    print(lid, '=>', res)
"
    sleep 30
done
