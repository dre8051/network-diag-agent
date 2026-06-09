"""
setup_gcp.py — 用 gws 的 OAuth token 自動設定 GCP Pub/Sub + Gmail Watch
不需要 gcloud，使用 Google REST API 直接操作

用法：
  source .venv/bin/activate
  python setup_gcp.py
"""

import json
import os
import subprocess
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "gen-lang-client-0237192169")
TOPIC_NAME = "gmail-network-diag"
TOPIC_FULL = f"projects/{PROJECT_ID}/topics/{TOPIC_NAME}"
SUBSCRIPTION_NAME = "gmail-diag-sub"
SUB_FULL = f"projects/{PROJECT_ID}/subscriptions/{SUBSCRIPTION_NAME}"
GMAIL_SA = "gmail-api-push@system.gserviceaccount.com"
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "me")


def get_gws_token() -> str:
    """從 gws keyring 取得 access token"""
    try:
        result = subprocess.run(
            ["gws", "gmail", "users", "getProfile", "--params", '{"userId":"me"}'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            print(f"❌ gws 呼叫失敗：{result.stderr}")
            sys.exit(1)

        # gws 成功 → token 在 keyring，透過 gcloud application-default 或直接取
        # 嘗試從 gcloud 取 token
        token_result = subprocess.run(
            ["/home/dre8051/google-cloud-sdk/bin/gcloud", "auth", "print-access-token"],
            capture_output=True, text=True, timeout=10
        )
        if token_result.returncode == 0:
            return token_result.stdout.strip()
    except Exception:
        pass

    # Fallback: 從 gws keyring 路徑讀
    try:
        import keyring
        token = keyring.get_password("gws", "access_token")
        if token:
            return token
    except Exception:
        pass

    print("❌ 無法取得 access token，請先執行 gcloud auth login")
    sys.exit(1)


def pubsub_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def create_topic(token: str) -> bool:
    print(f"[1/4] 建立 Pub/Sub topic: {TOPIC_FULL}")
    url = f"https://pubsub.googleapis.com/v1/{TOPIC_FULL}"
    resp = requests.put(url, headers=pubsub_headers(token), json={})

    if resp.status_code in (200, 409):  # 409 = already exists
        status = "已存在" if resp.status_code == 409 else "✅ 建立成功"
        print(f"   {status}")
        return True
    else:
        print(f"   ❌ 失敗 {resp.status_code}: {resp.text}")
        return False


def grant_gmail_publisher(token: str) -> bool:
    print(f"[2/4] 授權 Gmail SA 發布到 topic")
    url = f"https://pubsub.googleapis.com/v1/{TOPIC_FULL}:setIamPolicy"
    body = {
        "policy": {
            "bindings": [{
                "role": "roles/pubsub.publisher",
                "members": [f"serviceAccount:{GMAIL_SA}"]
            }]
        }
    }
    resp = requests.post(url, headers=pubsub_headers(token), json=body)
    if resp.status_code == 200:
        print("   ✅ 授權成功")
        return True
    else:
        print(f"   ❌ 失敗 {resp.status_code}: {resp.text}")
        return False


def create_subscription(token: str, push_endpoint: str) -> bool:
    print(f"[3/4] 建立 Pub/Sub subscription: {SUB_FULL}")
    url = f"https://pubsub.googleapis.com/v1/{SUB_FULL}"
    body = {
        "topic": TOPIC_FULL,
        "pushConfig": {
            "pushEndpoint": push_endpoint,
        },
        "ackDeadlineSeconds": 60,
    }
    resp = requests.put(url, headers=pubsub_headers(token), json=body)
    if resp.status_code in (200, 409):
        status = "已存在" if resp.status_code == 409 else "✅ 建立成功"
        print(f"   {status}")
        return True
    else:
        print(f"   ❌ 失敗 {resp.status_code}: {resp.text}")
        return False


def update_subscription_endpoint(token: str, push_endpoint: str) -> bool:
    """更新 push endpoint（ngrok 重啟後用）"""
    print(f"   更新 push endpoint → {push_endpoint}")
    url = f"https://pubsub.googleapis.com/v1/{SUB_FULL}"
    body = {
        "pushConfig": {
            "pushEndpoint": push_endpoint,
        },
        "updateMask": "pushConfig",
    }
    resp = requests.patch(url, headers=pubsub_headers(token), json=body)
    if resp.status_code == 200:
        print("   ✅ Endpoint 已更新")
        return True
    else:
        print(f"   ❌ 失敗 {resp.status_code}: {resp.text}")
        return False


def setup_gmail_watch() -> bool:
    print(f"[4/4] 設定 Gmail Watch → topic: {TOPIC_FULL}")
    result = subprocess.run(
        [
            "gws", "gmail", "users", "watch",
            "--params", json.dumps({"userId": "me"}),
            "--json", json.dumps({
                "labelIds": ["INBOX"],
                "topicName": TOPIC_FULL,
            }),
        ],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        data = json.loads(result.stdout)
        expiry_ms = int(data.get("expiration", 0))
        from datetime import datetime
        expiry_dt = datetime.fromtimestamp(expiry_ms / 1000)
        print(f"   ✅ Gmail Watch 設定成功")
        print(f"   historyId : {data.get('historyId')}")
        print(f"   過期時間  : {expiry_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        return True
    else:
        print(f"   ❌ Gmail Watch 失敗：{result.stderr}")
        print(f"   stdout: {result.stdout}")
        return False


def enable_apis(token: str):
    """啟用必要的 GCP API"""
    apis = ["pubsub.googleapis.com", "gmail.googleapis.com"]
    for api in apis:
        url = f"https://serviceusage.googleapis.com/v1/projects/{PROJECT_ID}/services/{api}:enable"
        resp = requests.post(url, headers=pubsub_headers(token), json={})
        if resp.status_code in (200, 409):
            print(f"   ✅ {api} 已啟用")
        else:
            print(f"   ⚠ {api}: {resp.status_code} {resp.text[:100]}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="設定 GCP Pub/Sub + Gmail Watch")
    parser.add_argument("--push-endpoint", help="Pub/Sub push endpoint URL（ngrok URL）")
    parser.add_argument("--update-endpoint", action="store_true", help="只更新 push endpoint")
    args = parser.parse_args()

    print("=" * 50)
    print("GCP Pub/Sub + Gmail Watch 自動設定")
    print(f"Project: {PROJECT_ID}")
    print(f"Gmail:   {GMAIL_ADDRESS}")
    print("=" * 50)
    print()

    token = get_gws_token()
    print(f"✅ Access token 取得成功\n")

    if args.update_endpoint:
        if not args.push_endpoint:
            print("❌ --update-endpoint 需要搭配 --push-endpoint")
            sys.exit(1)
        update_subscription_endpoint(token, args.push_endpoint)
        sys.exit(0)

    # 啟用 API
    print("[0/4] 啟用 GCP API")
    enable_apis(token)
    print()

    # 建 topic
    if not create_topic(token):
        sys.exit(1)

    # 授權
    grant_gmail_publisher(token)

    # 建 subscription
    push_endpoint = args.push_endpoint or "https://PLACEHOLDER.ngrok.io/pubsub/push"
    if not create_subscription(token, push_endpoint):
        # 可能已存在，嘗試更新
        update_subscription_endpoint(token, push_endpoint)

    # Gmail Watch
    print()
    if setup_gmail_watch():
        print()
        print("=" * 50)
        print("✅ 設定完成！")
        if "PLACEHOLDER" in push_endpoint:
            print()
            print("⚠  下一步：啟動 ngrok 後，執行：")
            print("   python setup_gcp.py --update-endpoint --push-endpoint https://xxxx.ngrok.io/pubsub/push")
        print("=" * 50)
    else:
        print("⚠  Pub/Sub 已設定，但 Gmail Watch 失敗（可能需要先啟用 Gmail API 並授權）")
