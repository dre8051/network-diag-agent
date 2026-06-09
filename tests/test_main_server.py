"""
Functional tests for main_server.py FastAPI endpoints
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("PASSPHRASE", "dragon2024")
os.environ.setdefault("SUBJECT_PREFIX", "[網路障礙回報]")
os.environ.setdefault("REPLY_TO_USER", "false")
os.environ.setdefault("GMAIL_ADDRESS", "test@example.com")
os.environ.setdefault("FABRIC_PATTERN", "network_analysis")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main_server import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestPubsubPushEndpoint:
    def test_missing_message_returns_200(self):
        """Pub/Sub 格式不對也要回 200，避免重試"""
        resp = client.post("/pubsub/push", json={})
        assert resp.status_code == 200

    def test_invalid_json_returns_200(self):
        resp = client.post("/pubsub/push", content=b"not json",
                           headers={"Content-Type": "application/json"})
        assert resp.status_code == 200

    def test_valid_pubsub_format_returns_200(self, monkeypatch):
        import base64, json
        import main_server

        # Mock Gmail history call so no credentials needed
        async def _fake_get_message_id(_): return None
        monkeypatch.setattr(main_server, "_get_latest_message_id", _fake_get_message_id)

        data = base64.b64encode(json.dumps({
            "messageId": "test-msg-001",
            "emailAddress": "test@example.com"
        }).encode()).decode()

        payload = {"message": {"data": data, "messageId": "pub-123"}}
        resp = client.post("/pubsub/push", json=payload)
        assert resp.status_code == 200


class TestTestTriggerEndpoint:
    def test_wrong_pass_rejected(self):
        resp = client.post("/test/trigger", json={
            "target_ip": "8.8.8.8",
            "passphrase": "wrongpass"
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_invalid_ip_rejected(self):
        resp = client.post("/test/trigger", json={
            "target_ip": "not-an-ip",
            "passphrase": "dragon2024"
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_valid_request_accepted(self):
        """驗證通過後應回 accepted（背景非同步跑，不等完成）"""
        resp = client.post("/test/trigger", json={
            "target_ip": "8.8.8.8",
            "passphrase": "dragon2024"
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"
