"""
fabric_runner.py — 呼叫 fabric CLI，pipe 測試結果，取得 AI 分析報告
"""

import logging
import os
import subprocess
import shutil

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

FABRIC_PATTERN = os.getenv("FABRIC_PATTERN", "network_analysis")
FABRIC_TIMEOUT = 120  # 秒


def analyze(summary_text: str) -> str:
    """
    將 summary_text pipe 進 fabric CLI，回傳 AI 分析報告文字
    失敗時 fallback 回傳原始摘要
    """
    # 確認 fabric CLI 存在
    fabric_path = shutil.which("fabric")
    if not fabric_path:
        logger.error("fabric CLI 不存在（找不到可執行檔），回傳原始測試結果")
        return _fallback(summary_text, "fabric CLI 未安裝")

    try:
        logger.info(f"[fabric] 呼叫 pattern: {FABRIC_PATTERN}")
        proc = subprocess.run(
            ["fabric", "--pattern", FABRIC_PATTERN],
            input=summary_text,
            capture_output=True,
            text=True,
            timeout=FABRIC_TIMEOUT,
            encoding="utf-8",
        )

        if proc.returncode != 0:
            stderr = proc.stderr.strip()
            logger.error(f"[fabric] 執行失敗（exit {proc.returncode}）：{stderr}")
            return _fallback(summary_text, f"fabric 錯誤：{stderr}")

        output = proc.stdout.strip()
        if not output:
            logger.warning("[fabric] 輸出為空，回傳原始測試結果")
            return _fallback(summary_text, "fabric 輸出為空")

        logger.info(f"[fabric] 分析完成，輸出 {len(output)} 字元")
        return output

    except subprocess.TimeoutExpired:
        logger.error(f"[fabric] 執行超時（>{FABRIC_TIMEOUT}s）")
        return _fallback(summary_text, "fabric 執行超時")
    except Exception as e:
        logger.error(f"[fabric] 未知錯誤：{e}")
        return _fallback(summary_text, str(e))


def _fallback(summary_text: str, reason: str) -> str:
    """fabric 失敗時的 fallback 格式"""
    return "\n".join([
        "---[用戶版]---",
        "AI 分析暫時無法使用，以下為原始測試數據，請聯繫工程師協助判讀。",
        "",
        "---[工程師版]---",
        f"[注意] fabric 分析失敗：{reason}",
        "",
        "=== 原始測試數據 ===",
        summary_text,
    ])
