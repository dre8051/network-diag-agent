"""
gmail_client.py — 讀取信件、解析內容、發送回信
"""

import base64
import email
import logging
import os
from email.mime.text import MIMEText
from typing import Optional

import googleapiclient.discovery
from googleapiclient.errors import HttpError

from gmail_auth import get_credentials

logger = logging.getLogger(__name__)


def _build_service():
    creds = get_credentials()
    return googleapiclient.discovery.build("gmail", "v1", credentials=creds)


def get_message(message_id: str) -> Optional[dict]:
    """
    讀取完整信件，回傳 {'subject': str, 'body': str, 'from': str, 'thread_id': str}
    失敗回傳 None
    """
    try:
        service = _build_service()
        msg = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        subject = headers.get("Subject", "")
        sender = headers.get("From", "")
        thread_id = msg.get("threadId", "")

        body = _extract_body(msg["payload"])

        logger.info(f"成功讀取信件 {message_id}，主旨：{subject}")
        return {
            "id": message_id,
            "thread_id": thread_id,
            "subject": subject,
            "from": sender,
            "body": body,
        }

    except HttpError as e:
        logger.error(f"Gmail API 錯誤（讀信 {message_id}）：{e}")
        return None
    except Exception as e:
        logger.error(f"讀信失敗（{message_id}）：{e}")
        return None


def _extract_body(payload: dict) -> str:
    """從 MIME payload 提取純文字，優先 text/plain"""
    mime_type = payload.get("mimeType", "")

    # 直接是 text/plain
    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return _decode_base64(data)

    # multipart：遞迴搜尋 text/plain，找不到再找 text/html
    if mime_type.startswith("multipart/"):
        parts = payload.get("parts", [])
        plain = None
        html = None
        for part in parts:
            if part.get("mimeType") == "text/plain":
                plain = _decode_base64(part.get("body", {}).get("data", ""))
            elif part.get("mimeType") == "text/html" and html is None:
                html = _decode_base64(part.get("body", {}).get("data", ""))
            elif part.get("mimeType", "").startswith("multipart/"):
                nested = _extract_body(part)
                if nested:
                    plain = nested
        if plain:
            return plain
        if html:
            return _strip_html(html)

    # fallback：直接讀 body data
    data = payload.get("body", {}).get("data", "")
    return _decode_base64(data)


def _decode_base64(data: str) -> str:
    if not data:
        return ""
    try:
        padded = data + "=" * (4 - len(data) % 4)
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _strip_html(html: str) -> str:
    import re
    clean = re.sub(r"<[^>]+>", "", html)
    return clean.strip()


def send_reply(original_message: dict, body: str) -> bool:
    """
    回覆原信，body 為純文字
    回傳 True/False
    """
    try:
        service = _build_service()
        subject = original_message.get("subject", "")
        to_addr = original_message.get("from", "")
        thread_id = original_message.get("thread_id", "")
        original_id = original_message.get("id", "")

        reply_subject = subject if subject.startswith("Re:") else f"Re: {subject}"

        mime = MIMEText(body, "plain", "utf-8")
        mime["To"] = to_addr
        mime["Subject"] = reply_subject
        mime["In-Reply-To"] = original_id
        mime["References"] = original_id

        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")

        service.users().messages().send(
            userId="me",
            body={"raw": raw, "threadId": thread_id},
        ).execute()

        logger.info(f"✅ 已回信給 {to_addr}，主旨：{reply_subject}")
        return True

    except HttpError as e:
        logger.error(f"Gmail API 錯誤（回信）：{e}")
        return False
    except Exception as e:
        logger.error(f"回信失敗：{e}")
        return False
