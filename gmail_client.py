"""
gmail_client.py — 讀取信件、解析內容、發送回信
改用 gws CLI，免去 Python SDK 和 credentials.json 的麻煩
"""

import base64
import json
import logging
import os
import subprocess
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

def run_gws(args: list) -> dict:
    """執行 gws cli 並回傳 JSON dict"""
    cmd = ["gws"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"gws 執行失敗: {' '.join(cmd)}\n{result.stderr}")
        return {}
    
    try:
        # 有些輸出會有 "Using keyring backend" 之類的 log
        # 尋找 { 開頭的地方
        out = result.stdout
        idx = out.find("{")
        if idx != -1:
            return json.loads(out[idx:])
        return {}
    except Exception as e:
        logger.error(f"無法解析 gws JSON 輸出: {e}")
        return {}

def get_message(message_id: str) -> Optional[dict]:
    try:
        msg = run_gws(["gmail", "users", "messages", "get", "--params", json.dumps({"userId": "me", "id": message_id, "format": "full"})])
        if not msg:
            return None

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        subject = headers.get("Subject", "")
        sender = headers.get("From", "")
        thread_id = msg.get("threadId", "")

        body = _extract_body(msg.get("payload", {}))

        logger.info(f"成功讀取信件 {message_id}，主旨：{subject}")
        return {
            "id": message_id,
            "thread_id": thread_id,
            "subject": subject,
            "from": sender,
            "body": body,
        }
    except Exception as e:
        logger.error(f"取得信件失敗：{e}")
        return None

def _extract_body(payload: dict) -> str:
    body = ""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"].get("data", "")
                if data:
                    body += base64.urlsafe_b64decode(data).decode("utf-8")
            elif "parts" in part:
                body += _extract_body(part)
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            body = base64.urlsafe_b64decode(data).decode("utf-8")
    return body

def send_reply(original_msg: dict, reply_text: str) -> bool:
    try:
        message = MIMEText(reply_text)
        message["to"] = original_msg["from"]
        message["subject"] = original_msg["subject"]
        if not message["subject"].startswith("Re:"):
            message["subject"] = "Re: " + message["subject"]
        
        message["In-Reply-To"] = original_msg["id"]
        message["References"] = original_msg["id"]

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        body = {
            "threadId": original_msg["thread_id"],
            "raw": raw_message
        }

        logger.info(f"發送回信給：{original_msg['from']}")
        
        result = subprocess.run(
            ["gws", "gmail", "users", "messages", "send", "--params", '{"userId": "me"}', "--json", json.dumps(body)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            logger.info("回信成功")
            return True
        else:
            logger.error(f"回信失敗：{result.stderr}")
            return False

    except Exception as e:
        logger.error(f"發送回信時發生錯誤：{e}")
        return False
