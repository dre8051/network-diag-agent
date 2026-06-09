"""
gmail_watch.py — 設定 Gmail Watch，訂閱收信事件（有效期 7 天）
每次執行會更新 watch，需每 6 天執行一次（可設 cron job）

用法：python3 gmail_watch.py
crontab: 0 9 */6 * * python3 /path/to/project/gmail_watch.py >> /path/to/project/logs/watch.log 2>&1
"""

import os
import sys
from datetime import datetime

from dotenv import load_dotenv
import googleapiclient.discovery

from gmail_auth import get_credentials

load_dotenv()

PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "projects/network-diag-project/topics/gmail-network-diag")


def setup_watch() -> dict:
    creds = get_credentials()
    service = googleapiclient.discovery.build("gmail", "v1", credentials=creds)

    request_body = {
        "labelIds": ["INBOX"],
        "topicName": PUBSUB_TOPIC,
    }

    result = service.users().watch(userId="me", body=request_body).execute()
    expiration_ms = int(result.get("expiration", 0))
    expiration_dt = datetime.fromtimestamp(expiration_ms / 1000)

    print(f"✅ Gmail Watch 設定成功")
    print(f"   historyId : {result.get('historyId')}")
    print(f"   過期時間  : {expiration_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   topic     : {PUBSUB_TOPIC}")

    return result


if __name__ == "__main__":
    try:
        setup_watch()
    except Exception as e:
        print(f"❌ Gmail Watch 設定失敗：{e}", file=sys.stderr)
        sys.exit(1)
