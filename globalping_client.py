"""
globalping_client.py — 呼叫 Globalping REST API 從台灣節點執行網路測試
"""

import logging
import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

API_BASE = "https://api.globalping.io/v1"
GLOBALPING_TOKEN = os.getenv("GLOBALPING_TOKEN", "")
POLL_INTERVAL = 2       # 秒
POLL_TIMEOUT = 120      # 最多等待秒數
PROBES_PER_TEST = 3     # 每項測試的節點數


def _headers() -> dict:
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if GLOBALPING_TOKEN:
        h["Authorization"] = f"Bearer {GLOBALPING_TOKEN}"
    return h


def _create_measurement(measurement_type: str, target: str, options: dict = None) -> Optional[str]:
    """發起測試，回傳 measurement ID"""
    # 如果 target 是 IP，跳過 dns 測試以免產生 400 Bad Request
    if measurement_type == "dns":
        import re
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", target):
            logger.info("[Globalping] 目標為 IP，自動略過 DNS 解析測試")
            return None

    payload = {
        "type": measurement_type,
        "target": target,
        "locations": [
            {"country": "TW"},  # 台灣
            {"country": "US"},  # 美國
            {"country": "JP"},  # 日本
            {"country": "DE"}   # 德國
        ],
        "limit": 4,
    }
    if options:
        payload["measurementOptions"] = options

    try:
        resp = requests.post(
            f"{API_BASE}/measurements",
            json=payload,
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        measurement_id = resp.json().get("id")
        logger.info(f"[Globalping] {measurement_type} 已發起，ID：{measurement_id}")
        return measurement_id
    except requests.RequestException as e:
        logger.error(f"[Globalping] {measurement_type} 請求失敗：{e}")
        return None


def _poll_result(measurement_id: str) -> Optional[dict]:
    """輪詢直到 status=finished 或超時"""
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        try:
            resp = requests.get(
                f"{API_BASE}/measurements/{measurement_id}",
                headers=_headers(),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            if status == "finished":
                return data
            elif status == "failed":
                logger.error(f"[Globalping] 測試失敗 {measurement_id}")
                return data
            time.sleep(POLL_INTERVAL)
        except requests.RequestException as e:
            logger.error(f"[Globalping] 輪詢錯誤 {measurement_id}：{e}")
            time.sleep(POLL_INTERVAL)

    logger.error(f"[Globalping] 輪詢超時 {measurement_id}")
    return None


def run_ping(target: str) -> dict:
    """執行 ping 測試，回傳結果 dict"""
    measurement_id = _create_measurement("ping", target)
    if not measurement_id:
        return {"type": "ping", "status": "error", "error": "無法發起測試"}

    result = _poll_result(measurement_id)
    if not result:
        return {"type": "ping", "status": "timeout", "error": "等待超時"}

    return {"type": "ping", "status": result.get("status"), "results": result.get("results", [])}


def run_traceroute(target: str) -> dict:
    """執行 traceroute 測試"""
    measurement_id = _create_measurement("traceroute", target)
    if not measurement_id:
        return {"type": "traceroute", "status": "error", "error": "無法發起測試"}

    result = _poll_result(measurement_id)
    if not result:
        return {"type": "traceroute", "status": "timeout", "error": "等待超時"}

    return {"type": "traceroute", "status": result.get("status"), "results": result.get("results", [])}


def run_dns(target: str) -> dict:
    """執行 DNS 解析測試"""
    import re
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", target):
        return {"type": "dns", "status": "skipped", "error": "目標為 IP 位址，不需執行 DNS 解析"}

    measurement_id = _create_measurement(
        "dns", target,
        options={"query": {"type": "A"}}
    )
    if not measurement_id:
        return {"type": "dns", "status": "error", "error": "無法發起測試"}

    result = _poll_result(measurement_id)
    if not result:
        return {"type": "dns", "status": "timeout", "error": "等待超時"}

    return {"type": "dns", "status": result.get("status"), "results": result.get("results", [])}


def run_all(target: str) -> dict:
    """
    依序執行 ping / traceroute / DNS，回傳彙整結果
    即使單項失敗也繼續執行其餘項目
    """
    logger.info(f"[Globalping] 開始對 {target} 執行完整測試（ping / traceroute / dns）")

    ping_result = run_ping(target)
    logger.info(f"[Globalping] ping 完成：{ping_result['status']}")

    traceroute_result = run_traceroute(target)
    logger.info(f"[Globalping] traceroute 完成：{traceroute_result['status']}")

    dns_result = run_dns(target)
    logger.info(f"[Globalping] dns 完成：{dns_result['status']}")

    return {
        "target": target,
        "ping": ping_result,
        "traceroute": traceroute_result,
        "dns": dns_result,
    }
