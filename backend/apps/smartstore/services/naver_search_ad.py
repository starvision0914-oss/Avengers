"""
네이버 검색광고 API 광고비 수집
Customer ID + Access License + Secret Key 방식 (HMAC-SHA256)
캠페인 타입별 분리: cpc(SHOPPING/WEB_SITE) | ai(SMART_SHOPPING/AI계열) | brand(BRAND_SEARCH)
"""
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
