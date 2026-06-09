"""
gmail_auth.py — 初次執行 OAuth2 授權，產生 token.json
用法：
  python3 gmail_auth.py          # 執行授權流程
  python3 gmail_auth.py --test   # 驗證 token 是否有效
"""

import argparse
import json
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def get_credentials() -> Credentials:
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds)
        return creds

    if not os.path.exists(CREDENTIALS_FILE):
        raise RuntimeError(f"找不到 {CREDENTIALS_FILE}，請先從 GCP Console 下載 OAuth2 憑證")

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    _save_token(creds)
    return creds


def _save_token(creds: Credentials) -> None:
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    print(f"✅ token.json 已儲存")


def test_token() -> bool:
    try:
        import googleapiclient.discovery

        creds = get_credentials()
        service = googleapiclient.discovery.build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        print(f"✅ token 有效，Gmail: {profile['emailAddress']}")
        return True
    except Exception as e:
        print(f"❌ token 驗證失敗：{e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="驗證 token 是否有效")
    args = parser.parse_args()

    try:
        if args.test:
            ok = test_token()
            sys.exit(0 if ok else 1)
        else:
            creds = get_credentials()
            print("✅ 授權完成，token.json 已產生")
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)
