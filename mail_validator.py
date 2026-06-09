"""
mail_validator.py — 驗證信件主旨格式、解析 body 欄位、驗證通關密碼
"""

import ipaddress
import logging
import os
import re
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

PASSPHRASE = os.getenv("PASSPHRASE", "")
SUBJECT_PREFIX = os.getenv("SUBJECT_PREFIX", "[網路障礙回報]")


def validate_subject(subject: str) -> bool:
    """
    驗證主旨是否符合 "{SUBJECT_PREFIX} {PASSPHRASE}" 格式
    """
    expected = f"{SUBJECT_PREFIX} {PASSPHRASE}"
    # 允許前後空白，但主旨必須完全一致
    result = subject.strip() == expected
    if not result:
        logger.warning(f"主旨不符格式，忽略。收到：{subject!r}，期待：{expected!r}")
    return result


def parse_body(body: str) -> Optional[dict]:
    """
    從信件 body 解析 IP: 和 PASS: 欄位
    回傳 {'ip': str, 'passphrase': str} 或 None
    """
    ip = None
    passphrase = None

    for line in body.splitlines():
        line = line.strip()
        if line.upper().startswith("IP:"):
            ip = line[3:].strip()
        elif line.upper().startswith("PASS:"):
            passphrase = line[5:].strip()

    if ip is None or passphrase is None:
        logger.warning(f"信件 body 缺少 IP 或 PASS 欄位")
        return None

    return {"ip": ip, "passphrase": passphrase}


def validate_pass(parsed_pass: str) -> bool:
    """
    驗證解析出的 PASS 是否與 .env PASSPHRASE 一致
    """
    result = parsed_pass == PASSPHRASE
    if not result:
        logger.warning(f"通關密碼驗證失敗，忽略。收到：{parsed_pass!r}")
    return result


def validate_ip(ip_str: str) -> bool:
    """
    驗證是否為合法的 IPv4 或 IPv6 位址
    """
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        logger.warning(f"IP 格式無效，忽略：{ip_str!r}")
        return False


def validate_message(subject: str, body: str) -> Optional[dict]:
    """
    一次性驗證整封信件，成功回傳 {'ip': str}，失敗回傳 None
    """
    if not validate_subject(subject):
        return None

    parsed = parse_body(body)
    if parsed is None:
        return None

    if not validate_pass(parsed["passphrase"]):
        return None

    if not validate_ip(parsed["ip"]):
        return None

    logger.info(f"信件驗證通過，目標 IP：{parsed['ip']}")
    return {"ip": parsed["ip"]}
