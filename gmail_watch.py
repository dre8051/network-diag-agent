"""
gmail_watch.py — 定期呼叫 Gmail API 更新 watch 狀態（每 7 天過期）
改用 gws CLI 實作
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/watch.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

TOPIC_NAME = os.getenv("PUBSUB_TOPIC")

def setup_watch():
    if not TOPIC_NAME:
        logger.error("環境變數缺少 PUBSUB_TOPIC")
        sys.exit(1)

    logger.info(f"開始設定 Gmail Watch → {TOPIC_NAME}")

    cmd = [
        "gws", "gmail", "users", "watch",
        "--params", json.dumps({"userId": "me"}),
        "--json", json.dumps({
            "labelIds": ["INBOX"],
            "topicName": TOPIC_NAME,
        })
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Gmail Watch 失敗: {result.stderr}")
        sys.exit(1)

    try:
        out = result.stdout
        idx = out.find("{")
        if idx != -1:
            data = json.loads(out[idx:])
            expiry_ms = int(data.get("expiration", 0))
            expiry_dt = datetime.fromtimestamp(expiry_ms / 1000)
            logger.info("✅ Gmail Watch 設定成功")
            logger.info(f"   historyId : {data.get('historyId')}")
            logger.info(f"   過期時間  : {expiry_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            logger.warning(f"Watch 成功，但無法解析輸出: {out}")
    except Exception as e:
        logger.error(f"解析回傳資料失敗: {e}")

if __name__ == "__main__":
    setup_watch()
