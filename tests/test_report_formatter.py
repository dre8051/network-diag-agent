"""
Unit tests for report_formatter.py
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import report_formatter


class TestParseAiReport:
    def test_full_report(self):
        output = """
---[用戶版]---
連線正常，延遲約 20ms。

---[工程師版]---
Ping avg=20ms loss=0%
"""
        user, eng = report_formatter.parse_ai_report(output)
        assert "連線正常" in user
        assert "Ping avg" in eng

    def test_missing_engineer_section(self):
        output = "---[用戶版]---\n連線正常"
        user, eng = report_formatter.parse_ai_report(output)
        assert "連線正常" in user
        assert "工程師版" in eng

    def test_no_markers_fallback(self):
        output = "Some random output without markers"
        user, eng = report_formatter.parse_ai_report(output)
        assert "解析失敗" in user
        assert "random output" in eng

    def test_engineer_only(self):
        output = "---[工程師版]---\n技術分析內容"
        user, eng = report_formatter.parse_ai_report(output)
        assert "技術分析" in eng


class TestFormatSummary:
    def test_basic_structure(self):
        results = {
            "target": "8.8.8.8",
            "ping": {"status": "finished", "results": []},
            "traceroute": {"status": "finished", "results": []},
            "dns": {"status": "error", "error": "API 失敗"},
        }
        summary = report_formatter.format_summary(results)
        assert "8.8.8.8" in summary
        assert "=== PING 結果 ===" in summary
        assert "=== TRACEROUTE 結果 ===" in summary
        assert "=== DNS 解析結果 ===" in summary
        assert "API 失敗" in summary

    def test_error_status(self):
        results = {
            "target": "1.1.1.1",
            "ping": {"status": "error", "error": "無法發起測試"},
            "traceroute": {"status": "error", "error": "無法發起測試"},
            "dns": {"status": "error", "error": "無法發起測試"},
        }
        summary = report_formatter.format_summary(results)
        assert "⚠" in summary


class TestSaveReport:
    def test_saves_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_formatter, "REPORTS_DIR", str(tmp_path))
        path = report_formatter.save_report("8.8.8.8", "用戶版內容", "工程師版內容", "原始摘要")
        assert os.path.exists(path)
        content = open(path, encoding="utf-8").read()
        assert "8.8.8.8" in content
        assert "用戶版內容" in content
        assert "工程師版內容" in content

    def test_ipv6_safe_filename(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_formatter, "REPORTS_DIR", str(tmp_path))
        path = report_formatter.save_report("2001:4860::1", "u", "e", "raw")
        filename = os.path.basename(path)
        assert ":" not in filename  # IPv6 冒號應被替換
