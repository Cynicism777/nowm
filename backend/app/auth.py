from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass

COOKIE_NAME = "nowm_session"


@dataclass(frozen=True)
class AuthConfig:
    invite_token: str
    session_secret: str
    session_days: int = 60
    cookie_secure: bool = True


def load_config() -> AuthConfig:
    invite = os.environ.get("INVITE_TOKEN", "").strip()
    secret = os.environ.get("SESSION_SECRET", "").strip()
    if not invite or not secret:
        raise RuntimeError("INVITE_TOKEN and SESSION_SECRET are required")
    days = int(os.environ.get("SESSION_DAYS", "60"))
    secure = os.environ.get("COOKIE_SECURE", "true").strip().lower() in (
        "1", "true", "yes", "on",
    )
    return AuthConfig(
        invite_token=invite,
        session_secret=secret,
        session_days=days,
        cookie_secure=secure,
    )


def invite_ok(provided: str, expected: str) -> bool:
    a = hashlib.sha256(provided.encode("utf-8")).digest()
    b = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(a, b)


def mint_session(secret: str, days: int, *, now: int | None = None) -> str:
    ts = int(now if now is not None else time.time())
    exp = ts + days * 86400
    msg = f"v1.{exp}"
    sig = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"),
                   hashlib.sha256).hexdigest()
    return f"{msg}.{sig}"


def verify_session(value: str, secret: str, *, now: int | None = None) -> bool:
    parts = value.split(".")
    if len(parts) != 3 or parts[0] != "v1":
        return False
    _, exp_s, sig = parts
    try:
        exp = int(exp_s)
    except ValueError:
        return False
    msg = f"v1.{exp}"
    expect = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"),
                      hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expect):
        return False
    ts = int(now if now is not None else time.time())
    return ts <= exp


def session_cookie_kwargs(cfg: AuthConfig) -> dict:
    return {
        "key": COOKIE_NAME,
        "httponly": True,
        "path": "/",
        "samesite": "lax",
        "secure": cfg.cookie_secure,
        "max_age": cfg.session_days * 86400,
    }
