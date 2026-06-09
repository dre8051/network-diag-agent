"""
report_formatter.py — 格式化測試結果、解析 AI 報告、儲存報告檔案
"""

import logging
import os
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

REPORTS_DIR = "reports"
USER_SECTION_MARKER = "---[用戶版]---"
ENGINEER_SECTION_MARKER = "---[工程師版]---"


def format_summary(results: dict) -> str:
    """
    將 Globalping 測試結果整理為純文字 summary
    results 結構：{'target': str, 'ping': dict, 'traceroute': dict, 'dns': dict}
    """
    target = results.get("target", "unknown")
    lines = [
        f"目標 IP：{target}",
        f"測試時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)",
        f"測試節點：台灣（TW）",
        "",
    ]

    # === PING ===
    lines.append("=== PING 結果 ===")
    ping = results.get("ping", {})
    if ping.get("status") in ("error", "timeout"):
        lines.append(f"  ⚠ 測試失敗：{ping.get('error', '未知錯誤')}")
    else:
        for probe in ping.get("results", []):
            probe_info = probe.get("probe", {})
            city = probe_info.get("city", "?")
            stats = probe.get("result", {}).get("stats", {})
            timings = probe.get("result", {}).get("timings", [])
            loss = stats.get("loss", "?")
            avg = stats.get("avg", "?")
            min_ = stats.get("min", "?")
            max_ = stats.get("max", "?")
            lines.append(f"  [{city}] 封包遺失：{loss}%，延遲 avg={avg}ms min={min_}ms max={max_}ms")
            for t in timings:
                lines.append(f"    RTT：{t.get('rtt', '?')}ms")

    lines.append("")

    # === TRACEROUTE ===
    lines.append("=== TRACEROUTE 結果 ===")
    traceroute = results.get("traceroute", {})
    if traceroute.get("status") in ("error", "timeout"):
        lines.append(f"  ⚠ 測試失敗：{traceroute.get('error', '未知錯誤')}")
    else:
        for probe in traceroute.get("results", []):
            probe_info = probe.get("probe", {})
            city = probe_info.get("city", "?")
            lines.append(f"  [{city}]")
            hops = probe.get("result", {}).get("hops", [])
            for hop in hops:
                hop_num = hop.get("resolvedAddress") or "*"
                timings = hop.get("timings", [])
                rtts = [str(t.get("rtt", "?")) for t in timings]
                rtt_str = " / ".join(rtts) if rtts else "* * *"
                host = hop.get("resolvedHostname") or hop.get("resolvedAddress") or "*"
                lines.append(f"    {host} ({hop_num}) → {rtt_str} ms")

    lines.append("")

    # === DNS ===
    lines.append("=== DNS 解析結果 ===")
    dns = results.get("dns", {})
    if dns.get("status") in ("error", "timeout"):
        lines.append(f"  ⚠ 測試失敗：{dns.get('error', '未知錯誤')}")
    else:
        for probe in dns.get("results", []):
            probe_info = probe.get("probe", {})
            city = probe_info.get("city", "?")
            answers = probe.get("result", {}).get("answers", [])
            lines.append(f"  [{city}]")
            if answers:
                for ans in answers:
                    lines.append(f"    {ans.get('name', '?')} → {ans.get('value', '?')} (TTL: {ans.get('ttl', '?')})")
            else:
                lines.append("    （無解析結果）")

    return "\n".join(lines)


def parse_ai_report(fabric_output: str) -> Tuple[str, str]:
    """
    從 fabric 輸出解析用戶版與工程師版
    回傳 (user_report, engineer_report)
    """
    user_report = ""
    engineer_report = ""

    if USER_SECTION_MARKER in fabric_output and ENGINEER_SECTION_MARKER in fabric_output:
        # 找到兩個 marker
        user_start = fabric_output.index(USER_SECTION_MARKER) + len(USER_SECTION_MARKER)
        eng_start = fabric_output.index(ENGINEER_SECTION_MARKER)
        eng_content_start = eng_start + len(ENGINEER_SECTION_MARKER)

        user_report = fabric_output[user_start:eng_start].strip()
        engineer_report = fabric_output[eng_content_start:].strip()

        logger.info("✅ 成功解析 AI 報告（用戶版 + 工程師版）")
    elif USER_SECTION_MARKER in fabric_output:
        # 只有用戶版
        user_start = fabric_output.index(USER_SECTION_MARKER) + len(USER_SECTION_MARKER)
        user_report = fabric_output[user_start:].strip()
        engineer_report = "（AI 報告未包含工程師版）\n\n" + fabric_output
    elif ENGINEER_SECTION_MARKER in fabric_output:
        # 只有工程師版
        eng_start = fabric_output.index(ENGINEER_SECTION_MARKER) + len(ENGINEER_SECTION_MARKER)
        engineer_report = fabric_output[eng_start:].strip()
        user_report = "AI 報告格式解析失敗，請查看原始輸出"
    else:
        # 格式解析失敗，整個視為工程師版
        logger.warning("AI 報告不含預期分隔標記，以完整輸出作為工程師版")
        engineer_report = fabric_output
        user_report = "AI 報告格式解析失敗，請查看原始輸出"

    return user_report, engineer_report


def save_report(ip: str, user_report: str, engineer_report: str, raw_summary: str) -> str:
    """
    儲存完整報告到 reports/report_{ip}_{timestamp}.txt
    回傳儲存路徑
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_ip = ip.replace(":", "_")  # IPv6 處理
    filename = f"report_{safe_ip}_{timestamp}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)

    content = "\n".join([
        f"{'='*60}",
        f"國際連線診斷報告",
        f"目標 IP：{ip}",
        f"產出時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"{'='*60}",
        "",
        f"{USER_SECTION_MARKER}",
        user_report,
        "",
        f"{ENGINEER_SECTION_MARKER}",
        engineer_report,
        "",
        "=== 原始測試數據 ===",
        raw_summary,
    ])

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"✅ 報告已儲存：{filepath}")
    return filepath
