"""
test_trigger.py — 模擬 Pub/Sub push，本地測試診斷流程
用法：
  python3 test_trigger.py --target 8.8.8.8 --pass dragon2024
  python3 test_trigger.py --target 8.8.8.8 --pass dragon2024 --host http://localhost:8000
"""

import argparse
import base64
import json
import time

import requests


def simulate_pubsub_push(target_ip: str, passphrase: str, host: str):
    """
    建立一封模擬信件的 Pub/Sub push payload，直接 POST 到本地 server
    繞過 Gmail，直接測試 process_email 流程

    注意：這個方法直接呼叫 /test/trigger（測試專用端點），
    因為真實的 Pub/Sub 流程需要 Gmail historyId
    """
    print(f"[test] 目標 IP：{target_ip}")
    print(f"[test] 通關密碼：{passphrase}")
    print(f"[test] Server：{host}")
    print()

    payload = {
        "target_ip": target_ip,
        "passphrase": passphrase,
    }

    try:
        resp = requests.post(
            f"{host}/test/trigger",
            json=payload,
            timeout=10,
        )
        print(f"[test] HTTP {resp.status_code}")
        print(f"[test] 回應：{resp.json()}")
        if resp.status_code == 200:
            print()
            print("[test] ✅ 診斷已在背景觸發，請查看 server console 輸出")
            print("[test] 約 60-120 秒後查看 reports/ 目錄")
    except requests.ConnectionError:
        print(f"[test] ❌ 無法連線到 {host}，請確認 main_server.py 已啟動")
    except Exception as e:
        print(f"[test] ❌ 錯誤：{e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="模擬 Pub/Sub push 觸發診斷")
    parser.add_argument("--target", required=True, help="目標 IP（例如 8.8.8.8）")
    parser.add_argument("--pass", dest="passphrase", required=True, help="通關密碼")
    parser.add_argument("--host", default="http://localhost:8000", help="Server URL")
    args = parser.parse_args()

    simulate_pubsub_push(args.target, args.passphrase, args.host)
