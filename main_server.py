"""
main_server.py - FastAPI service, receives Pub/Sub push, runs diagnosis async.
NOTE: /test/trigger endpoint is for local testing only. Remove or whitelist in production.
Launch: python main_server.py  (or: uvicorn main_server:app --host 0.0.0.0 --port 8000)
"""

import base64
import json
import logging
import os
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Request, Response

from fabric_runner import analyze
from gmail_client import get_message, send_reply
from globalping_client import run_all
from mail_validator import validate_message
from report_formatter import format_summary, parse_ai_report, save_report

# ─── 初始化 ────────────────────────────────────────────────
load_dotenv()

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/server.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

REPLY_TO_USER = os.getenv("REPLY_TO_USER", "true").lower() == "true"

# ─── 簡易去重快取（in-memory，TTL 60s）────────────────────
_seen_message_ids: OrderedDict[str, float] = OrderedDict()
_DEDUP_TTL = 60  # 秒


def _is_duplicate(message_id: str) -> bool:
    now = time.time()
    # 清理過期 ID
    expired = [k for k, v in _seen_message_ids.items() if now - v > _DEDUP_TTL]
    for k in expired:
        del _seen_message_ids[k]

    if message_id in _seen_message_ids:
        logger.warning(f"重複 message ID，忽略：{message_id}")
        return True

    _seen_message_ids[message_id] = now
    return False


# ─── FastAPI App ────────────────────────────────────────────
app = FastAPI(title="Network Diag Agent", version="1.0.0")


class TestTriggerRequest(BaseModel):
    target_ip: str
    passphrase: str


@app.get("/health")
async def health():
    return {"status": "ok", "service": "network-diag-agent"}


@app.post("/test/trigger")
async def test_trigger(req: TestTriggerRequest, background_tasks: BackgroundTasks):
    """
    測試用端點：直接指定 IP 和 PASS，繞過 Gmail / Pub/Sub 流程
    僅供本地驗證使用
    """
    import mail_validator
    from report_formatter import format_summary, parse_ai_report, save_report
    from globalping_client import run_all as _run_all
    from fabric_runner import analyze as _analyze

    subject = f"{os.getenv('SUBJECT_PREFIX', '[網路障礙回報]')} {req.passphrase}"
    body = f"IP: {req.target_ip}\nPASS: {req.passphrase}"

    validated = validate_message(subject, body)
    if not validated:
        return {"status": "rejected", "reason": "驗證失敗，請確認 IP 和 PASS"}

    fake_msg = {
        "id": "test-trigger",
        "thread_id": "test-thread",
        "subject": subject,
        "from": os.getenv("GMAIL_ADDRESS", "test@example.com"),
        "body": body,
    }

    async def _run():
        logger.info(f"[TEST] 開始診斷 IP={req.target_ip}")
        results = _run_all(req.target_ip)
        summary = format_summary(results)
        ai_output = _analyze(summary)
        user_report, engineer_report = parse_ai_report(ai_output)
        path = save_report(req.target_ip, user_report, engineer_report, summary)
        logger.info(f"[TEST] 診斷完成，報告：{path}")
        if REPLY_TO_USER:
            send_reply(fake_msg, user_report)

    background_tasks.add_task(_run)
    return {"status": "accepted", "message": f"診斷已觸發，目標 IP：{req.target_ip}"}


@app.post("/pubsub/push")
async def pubsub_push(request: Request, background_tasks: BackgroundTasks):
    """
    接收 Google Cloud Pub/Sub push 通知
    立即回傳 200，背景非同步執行診斷
    """
    try:
        body = await request.json()
    except Exception:
        logger.warning("Pub/Sub push：無法解析 JSON body")
        return Response(status_code=200)

    message = body.get("message", {})
    if not message:
        logger.warning("Pub/Sub push：缺少 message 欄位")
        return Response(status_code=200)

    # Decode base64 data
    raw_data = message.get("data", "")
    try:
        decoded = base64.b64decode(raw_data).decode("utf-8")
        data = json.loads(decoded)
    except Exception as e:
        logger.warning(f"Pub/Sub push：data decode 失敗：{e}")
        return Response(status_code=200)

    # 提取 Gmail message ID（Pub/Sub Gmail push notification 格式）
    gmail_message_id = data.get("messageId") or data.get("historyId")
    email_address = data.get("emailAddress", "")

    if not gmail_message_id:
        logger.warning(f"Pub/Sub push：找不到 Gmail message ID，data={decoded!r}")
        return Response(status_code=200)

    gmail_message_id = str(gmail_message_id)

    # 去重
    if _is_duplicate(gmail_message_id):
        return Response(status_code=200)

    logger.info(f"收到 Pub/Sub 通知，Gmail historyId/messageId：{gmail_message_id}，email：{email_address}")

    # 背景執行診斷
    background_tasks.add_task(process_email, gmail_message_id)
    return Response(status_code=200)


async def process_email(history_id: str):
    """
    完整診斷流程：
    讀信 → 驗證 → Globalping → fabric → 儲存報告 → 回信
    """
    logger.info(f"═══ 開始診斷流程 historyId={history_id} ═══")

    # Step 1: 從 historyId 取得最新信件 ID
    # Gmail Watch 通知只包含 historyId，需用 history API 取得 message ID
    message_id = await _get_latest_message_id(history_id)
    if not message_id:
        logger.warning(f"找不到對應 historyId={history_id} 的信件 ID")
        return

    # Step 2: 讀取完整信件
    msg = get_message(message_id)
    if not msg:
        logger.error(f"無法讀取信件 {message_id}")
        return

    logger.info(f"收到信件，主旨：{msg['subject']}")

    # Step 3: 驗證信件
    validated = validate_message(msg["subject"], msg["body"])
    if not validated:
        logger.info("信件驗證未通過，忽略")
        return

    target_ip = validated["ip"]
    logger.info(f"收到信件，開始診斷 IP：{target_ip}")

    # Step 4: Globalping 測試
    logger.info(f"[診斷] 呼叫 Globalping API，目標：{target_ip}")
    results = run_all(target_ip)

    # Step 5: 整理純文字摘要
    summary = format_summary(results)
    logger.info(f"[診斷] 測試結果整理完成，{len(summary)} 字元")

    # Step 6: fabric AI 分析
    logger.info("[診斷] 呼叫 fabric 進行 AI 分析...")
    ai_output = analyze(summary)

    # Step 7: 解析雙軌報告
    user_report, engineer_report = parse_ai_report(ai_output)

    # Step 8: 儲存報告
    report_path = save_report(target_ip, user_report, engineer_report, summary)
    logger.info(f"[診斷] 報告已儲存：{report_path}")

    # Step 9: 回信（選配）
    if REPLY_TO_USER:
        reply_body = "\n".join([
            "您好，以下是您回報 IP 的國際連線診斷結果：",
            "",
            user_report,
            "",
            "---",
            "此信由自動診斷系統發送，完整工程師版報告已另行保存。",
        ])
        success = send_reply(msg, reply_body)
        if success:
            logger.info("[診斷] 已回信給用戶")
        else:
            logger.error("[診斷] 回信失敗，但報告已儲存")
    else:
        logger.info("[診斷] 回信功能已關閉，僅儲存報告")

    logger.info(f"═══ 診斷流程完成 IP={target_ip} ═══")


async def _get_latest_message_id(history_id: str) -> Optional[str]:
    """
    透過 Gmail history API 取得 historyId 對應的最新 message ID
    """
    try:
        import googleapiclient.discovery
        from gmail_auth import get_credentials

        creds = get_credentials()
        service = googleapiclient.discovery.build("gmail", "v1", credentials=creds)

        # 用 historyId 查詢 history list
        history = service.users().history().list(
            userId="me",
            startHistoryId=history_id,
            historyTypes=["messageAdded"],
            labelId="INBOX",
        ).execute()

        changes = history.get("history", [])
        if not changes:
            # historyId 之後沒有新信件，可能是舊 history ID 或已處理
            logger.info(f"historyId={history_id} 之後無新信件")
            return None

        # 取最後一封新信件
        for change in reversed(changes):
            messages_added = change.get("messagesAdded", [])
            if messages_added:
                return messages_added[-1]["message"]["id"]

        return None

    except Exception as e:
        logger.error(f"取得 message ID 失敗：{e}")
        return None


if __name__ == "__main__":
    uvicorn.run(
        "main_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
