import time
import pytest
from app import auth


def test_invite_ok_accepts_match():
    assert auth.invite_ok("abc", "abc") is True
    assert auth.invite_ok("abc", "abd") is False
    assert auth.invite_ok("", "abd") is False


def test_mint_and_verify_roundtrip():
    secret = "test-secret-please-change"
    token = auth.mint_session(secret, days=60, now=1_700_000_000)
    assert auth.verify_session(token, secret, now=1_700_000_000) is True
    assert auth.verify_session(token, secret, now=1_700_000_000 + 60 * 86400 + 1) is False
    assert auth.verify_session(token, "other-secret", now=1_700_000_000) is False
    assert auth.verify_session("v1.1.deadbeef", secret, now=1_700_000_000) is False
    assert auth.verify_session("garbage", secret, now=1_700_000_000) is False


def test_load_config_requires_env(monkeypatch):
    monkeypatch.delenv("INVITE_TOKEN", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        auth.load_config()
