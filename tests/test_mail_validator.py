"""
Unit tests for mail_validator.py
"""
import os
import sys

import pytest

# 設定測試用環境變數（不依賴 .env）
os.environ.setdefault("PASSPHRASE", "dragon2024")
os.environ.setdefault("SUBJECT_PREFIX", "[網路障礙回報]")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import mail_validator  # noqa: E402


class TestValidateSubject:
    def test_valid_subject(self):
        assert mail_validator.validate_subject("[網路障礙回報] dragon2024") is True

    def test_wrong_passphrase(self):
        assert mail_validator.validate_subject("[網路障礙回報] wrongpass") is False

    def test_wrong_prefix(self):
        assert mail_validator.validate_subject("[其他主旨] dragon2024") is False

    def test_empty_subject(self):
        assert mail_validator.validate_subject("") is False

    def test_extra_whitespace_stripped(self):
        assert mail_validator.validate_subject("  [網路障礙回報] dragon2024  ") is True


class TestParseBody:
    def test_valid_body(self):
        body = "IP: 8.8.8.8\nPASS: dragon2024"
        result = mail_validator.parse_body(body)
        assert result == {"ip": "8.8.8.8", "passphrase": "dragon2024"}

    def test_missing_ip(self):
        assert mail_validator.parse_body("PASS: dragon2024") is None

    def test_missing_pass(self):
        assert mail_validator.parse_body("IP: 8.8.8.8") is None

    def test_extra_whitespace(self):
        body = "IP:  203.69.1.1  \nPASS:  dragon2024  "
        result = mail_validator.parse_body(body)
        assert result["ip"] == "203.69.1.1"
        assert result["passphrase"] == "dragon2024"

    def test_case_insensitive_keys(self):
        body = "ip: 8.8.8.8\npass: dragon2024"
        result = mail_validator.parse_body(body)
        assert result is not None


class TestValidatePass:
    def test_correct_pass(self):
        assert mail_validator.validate_pass("dragon2024") is True

    def test_wrong_pass(self):
        assert mail_validator.validate_pass("wrong") is False

    def test_empty_pass(self):
        assert mail_validator.validate_pass("") is False


class TestValidateIP:
    def test_valid_ipv4(self):
        assert mail_validator.validate_ip("8.8.8.8") is True

    def test_valid_ipv4_private(self):
        assert mail_validator.validate_ip("203.69.1.100") is True

    def test_valid_ipv6(self):
        assert mail_validator.validate_ip("2001:4860:4860::8888") is True

    def test_invalid_ip(self):
        assert mail_validator.validate_ip("999.999.999.999") is False

    def test_hostname(self):
        assert mail_validator.validate_ip("google.com") is False

    def test_empty(self):
        assert mail_validator.validate_ip("") is False


class TestValidateMessage:
    def test_full_valid_flow(self):
        subject = "[網路障礙回報] dragon2024"
        body = "IP: 8.8.8.8\nPASS: dragon2024"
        result = mail_validator.validate_message(subject, body)
        assert result == {"ip": "8.8.8.8"}

    def test_wrong_subject(self):
        result = mail_validator.validate_message("random", "IP: 8.8.8.8\nPASS: dragon2024")
        assert result is None

    def test_wrong_pass_in_body(self):
        result = mail_validator.validate_message(
            "[網路障礙回報] dragon2024",
            "IP: 8.8.8.8\nPASS: wrong"
        )
        assert result is None

    def test_invalid_ip(self):
        result = mail_validator.validate_message(
            "[網路障礙回報] dragon2024",
            "IP: not-an-ip\nPASS: dragon2024"
        )
        assert result is None
