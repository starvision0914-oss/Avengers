"""
네이버 검색광고 API 광고비 수집
Customer ID + Access License + Secret Key 방식 (HMAC-SHA256)
캠페인 타입별 분리: cpc(SHOPPING/WEB_SITE) | ai(SMART_SHOPPING/AI계열) | brand(BRAND_SEARCH)

상품별 광고비:
  공개 NCC API(api.naver.com)는 SHOPPING 캠페인 stats를 반환하지 않음.
  광고센터 내부 API(ads.naver.com/apis/sa/api/stats POST + X-AD-customer-id 헤더)를 사용.
  쿠키 파일(naver_ads_cookies.json)에서 세션 로드.
"""
import os
import time
import hmac
import hashlib
import base64
import json
import logging
from datetime import date

import requests

logger = logging.getLogger('smartstore')

BASE_URL = "https://api.naver.com"
_INTERNAL_STATS_URL = "https://ads.naver.com/apis/sa/api/stats"
_COOKIE_FILE = os.path.join(os.path.dirname(__file__), '../../../crawlers/naver_ads_cookies.json')

# campaignTp → ad_type 매핑
_TYPE_MAP = {
    "SHOPPING": "cpc",
    "WEB_SITE": "cpc",
    "BRAND_SEARCH": "brand",
    "SMART_SHOPPING": "ai",
    "SHOPPING_FEED": "ai",
}


def _campaign_to_ad_type(camp: dict) -> str:
    tp = camp.get("campaignTp", "")
    name = camp.get("name", "")
    if tp in _TYPE_MAP:
        return _TYPE_MAP[tp]
    # 이름에 AI 포함 시 ai로 분류
    if "AI" in name.upper() or "ai" in name.lower():
        return "ai"
    return "cpc"


def _get(customer_id: str, access_license: str, secret_key: str, path: str, params: dict = None):
    ts = str(round(time.time() * 1000))
    message = f"{ts}.GET.{path}"
    sig = hmac.new(bytes(secret_key, "utf-8"), message.encode("utf-8"), digestmod=hashlib.sha256).digest()
    headers = {
        "X-Timestamp": ts,
        "X-API-KEY": access_license,
        "X-Customer": str(customer_id),
        "X-Signature": base64.b64encode(sig).decode(),
        "Content-Type": "application/json",
    }
    r = requests.get(BASE_URL + path, headers=headers, params=params, timeout=15)
    if not r.ok:
        logger.warning("Naver SearchAd API error %s %s: %s", path, r.status_code, r.text[:200])
    return r


def fetch_campaigns(customer_id: str, access_license: str, secret_key: str) -> list:
    r = _get(customer_id, access_license, secret_key, "/ncc/campaigns")
    return r.json() or [] if r.ok else []


def fetch_daily_cost_by_type(customer_id: str, access_license: str, secret_key: str,
                              since: str, until: str) -> dict:
    """
    캠페인 타입별 일별 광고비 합산
    Returns: {(date_str, ad_type): {"cost":..., "click":..., ...}, ...}
    """
    campaigns = fetch_campaigns(customer_id, access_license, secret_key)
    if not campaigns:
        return {}

    result = {}  # (date, ad_type) -> totals

    fields = json.dumps([
        {"field": "cost"}, {"field": "clkCnt"},
        {"field": "impCnt"}, {"field": "convAmt"},
    ])

    for camp in campaigns:
        camp_id = camp.get("nccCampaignId")
        if not camp_id:
            continue
        ad_type = _campaign_to_ad_type(camp)

        params = {
            "fields": fields,
            "timeRange": json.dumps({"since": since, "until": until}),
            "timeUnit": "DAY",
            "type": "CAMPAIGN",
            "id": camp_id,
        }
        r = _get(customer_id, access_license, secret_key, "/stats", params)
        if not r.ok:
            continue

        for row in r.json().get("data", []):
            d = row.get("dateStart")
            key = (d, ad_type)
            if key not in result:
                result[key] = {"cost": 0, "click": 0, "impression": 0, "conversion_amount": 0}
            result[key]["cost"] += int(row.get("cost", 0) or 0)
            result[key]["click"] += int(row.get("clkCnt", 0) or 0)
            result[key]["impression"] += int(row.get("impCnt", 0) or 0)
            result[key]["conversion_amount"] += int(row.get("convAmt", 0) or 0)

        time.sleep(0.2)

    return result


def _save_daily(account, daily: dict, force_type: str = None):
    from apps.smartstore.models import SmartStoreAdCost
    upserted = 0
    for (date_str, ad_type), vals in daily.items():
        SmartStoreAdCost.objects.update_or_create(
            account=account,
            date=date_str,
            ad_type=force_type or ad_type,
            defaults={
                "cost": vals["cost"],
                "click": vals["click"],
                "impression": vals["impression"],
                "conversion_amount": vals["conversion_amount"],
            },
        )
        upserted += 1
    return upserted


def fetch_adgroups(customer_id: str, access_license: str, secret_key: str,
                   campaign_id: str) -> list:
    r = _get(customer_id, access_license, secret_key, "/ncc/adgroups",
             params={"nccCampaignId": campaign_id})
    return r.json() or [] if r.ok else []


def fetch_ads(customer_id: str, access_license: str, secret_key: str,
              adgroup_id: str) -> list:
    r = _get(customer_id, access_license, secret_key, "/ncc/ads",
             params={"nccAdgroupId": adgroup_id})
    return r.json() or [] if r.ok else []


def _internal_stats_session(login_id: str):
    """쿠키 파일에서 광고센터 내부 API 세션 생성. (sess, xsrf_token) 반환."""
    cookie_file = os.path.normpath(os.path.join(os.path.dirname(__file__), '../../../crawlers/naver_ads_cookies.json'))
    if not os.path.exists(cookie_file):
        return None, ''
    try:
        with open(cookie_file) as f:
            data = json.load(f)
        cookies = data.get(login_id, [])
        if not cookies:
            return None, ''
        sess = requests.Session()
        xsrf = ''
        for c in cookies:
            sess.cookies.set(c['name'], c['value'], domain=c.get('domain', '.naver.com'))
            if c['name'] == 'XSRF-TOKEN':
                xsrf = c['value']
        return sess, xsrf
    except Exception as e:
        logger.warning('_internal_stats_session 오류: %s', e)
        return None, ''


def _internal_stats_post(sess, xsrf: str, customer_id: str, ids: str,
                         since: str, until: str, batch_size: int = 100) -> dict:
    """
    광고센터 내부 stats API POST 호출 (ids 배치 분할).
    Returns: {nad_id: {"cost": ..., "click": ..., "impression": ..., "conv_cnt": ..., "conv_amt": ...}}
    """
    id_list = [i.strip() for i in ids.split(',') if i.strip()]
    result = {}
    for i in range(0, len(id_list), batch_size):
        batch = ','.join(id_list[i:i + batch_size])
        payload = {
            'ids': batch,
            'fields': ['clkCnt', 'impCnt', 'salesAmtMicros', 'convAmtMicros', 'ccnt'],
            'timeIncrement': 'allDays',
            'timeRange': {'since': since, 'until': until},
        }
        headers = {
            'Content-Type': 'application/json',
            'X-AD-customer-id': str(customer_id),
            'X-XSRF-TOKEN': xsrf,
            'X-Accept-Language': 'ko',
            'Referer': 'https://ads.naver.com/',
            'Cache-control': 'no-cache, no-store, must-revalidate',
        }
        try:
            r = sess.post(_INTERNAL_STATS_URL, json=payload, headers=headers, timeout=20)
            if r.ok:
                for row in r.json().get('data', []):
                    nid = row.get('id', '')
                    cost_micros = int(row.get('salesAmtMicros', 0) or 0)
                    result[nid] = {
                        'cost': cost_micros // 1_000_000,
                        'click': int(row.get('clkCnt', 0) or 0),
                        'impression': int(row.get('impCnt', 0) or 0),
                        'conv_cnt': int(row.get('ccnt', 0) or 0),
                        'conv_amt': int(row.get('convAmtMicros', 0) or 0) // 1_000_000,
                    }
        except Exception as e:
            logger.warning('_internal_stats_post 오류: %s', e)
        time.sleep(0.3)
    return result


def fetch_product_stats(customer_id: str, access_license: str, secret_key: str,
                        since: str, until: str, login_id: str = '') -> list:
    """
    상품별 광고비 합산 (광고센터 내부 API 사용, 쿠키 세션 필요)
    - 소재 목록: 공개 NCC API (api.naver.com/ncc/ads)
    - 통계: 내부 API (ads.naver.com/apis/sa/api/stats POST + X-AD-customer-id)
    Returns: [{"product_no": ..., "product_name": ..., "cost": ..., ...}, ...]
    """
    if not login_id:
        return []

    sess, xsrf = _internal_stats_session(login_id)
    if not sess:
        logger.warning('fetch_product_stats: 쿠키 없음 login_id=%s', login_id)
        return []

    campaigns = fetch_campaigns(customer_id, access_license, secret_key)
    if not campaigns:
        return []

    # 전체 소재 수집 (ad_id → product_no/name 매핑)
    ad_to_product = {}  # nccAdId -> {product_no, product_name}

    for camp in campaigns:
        camp_id = camp.get("nccCampaignId")
        if not camp_id:
            continue
        adgroups = fetch_adgroups(customer_id, access_license, secret_key, camp_id)
        time.sleep(0.2)

        for ag in adgroups:
            ag_id = ag.get("nccAdgroupId")
            if not ag_id:
                continue
            ads = fetch_ads(customer_id, access_license, secret_key, ag_id)
            time.sleep(0.2)
            for ad in ads:
                rd = ad.get("referenceData", {}) or {}
                mall_pid = rd.get("mallProductId")
                if mall_pid:
                    ad_to_product[ad["nccAdId"]] = {
                        "product_no": str(mall_pid),
                        "product_name": rd.get("productTitle", ""),
                    }

    if not ad_to_product:
        return []

    logger.info('fetch_product_stats: 소재 %d개, login_id=%s', len(ad_to_product), login_id)

    # 내부 stats API 일괄 조회
    all_ids = ','.join(ad_to_product.keys())
    stats_by_id = _internal_stats_post(sess, xsrf, customer_id, all_ids, since, until)

    # product_no 기준으로 집계
    product_map = {}
    for nad_id, pinfo in ad_to_product.items():
        st = stats_by_id.get(nad_id)
        if not st:
            continue
        pno = pinfo["product_no"]
        if pno not in product_map:
            product_map[pno] = {
                "product_no": pno,
                "product_name": pinfo["product_name"],
                "cost": 0, "click": 0, "impression": 0,
                "conversion_count": 0, "conversion_amount": 0,
            }
        p = product_map[pno]
        if pinfo["product_name"] and not p["product_name"]:
            p["product_name"] = pinfo["product_name"]
        p["cost"] += st["cost"]
        p["click"] += st["click"]
        p["impression"] += st["impression"]
        p["conversion_count"] += st["conv_cnt"]
        p["conversion_amount"] += st["conv_amt"]

    return list(product_map.values())


def sync_ad_cost(account, since: str = None, until: str = None) -> dict:
    has_cpc = bool(account.naver_ad_customer_id and account.naver_ad_access_license and account.naver_ad_secret_key)
    has_ai  = bool(account.naver_ad_ai_customer_id and account.naver_ad_ai_access_license and account.naver_ad_ai_secret_key)

    if not has_cpc and not has_ai:
        return {"skipped": True, "reason": "API 키 미등록"}

    if not since:
        today = date.today()
        since = f"{today.year}-{today.month:02d}-01"
    if not until:
        until = date.today().strftime("%Y-%m-%d")

    logger.info("Naver SearchAd sync: account=%s cpc=%s ai=%s %s~%s",
                account.id, has_cpc, has_ai, since, until)

    upserted = 0

    # CPC 계정 수집 (캠페인 타입으로 자동 분류)
    if has_cpc:
        daily = fetch_daily_cost_by_type(
            account.naver_ad_customer_id,
            account.naver_ad_access_license,
            account.naver_ad_secret_key,
            since, until,
        )
        upserted += _save_daily(account, daily)

    # AI 계정 수집 → 무조건 ad_type='ai'로 강제 저장
    if has_ai:
        daily_ai = fetch_daily_cost_by_type(
            account.naver_ad_ai_customer_id,
            account.naver_ad_ai_access_license,
            account.naver_ad_ai_secret_key,
            since, until,
        )
        upserted += _save_daily(account, daily_ai, force_type="ai")

    return {"upserted": upserted, "since": since, "until": until, "account": str(account)}
