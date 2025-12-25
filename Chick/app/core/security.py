# app/core/security.py
from __future__ import annotations
import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Tuple

import jwt  # PyJWT
from app.core.config import settings


# ---- 時間工具 ----
def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---- Access Token (JWT) ----
def create_access_token(
    *,
    user_id: int,
    is_guest: bool,
    expires_minutes: int | None = None,
) -> Tuple[str, int, datetime]:
    """
    產生 Access Token（JWT, HS256）
    回傳：(jwt_string, expires_in_seconds, expires_at_utc)
    """
    exp_minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    now = utcnow()
    expires_at = now + timedelta(minutes=exp_minutes)

    payload = {
        "sub": str(user_id),
        "is_guest": bool(is_guest),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    expires_in = int(expires_at.timestamp() - time.time())
    return token, expires_in, expires_at


# ---- Refresh Token (明文 + 雜湊) ----
def generate_refresh_token() -> str:
    """
    產生高熵的 Refresh Token 明文（只在回應時提供一次）
    """
    # 43~64字元左右的 URL-safe 隨機字串
    return secrets.token_urlsafe(48)


def hash_refresh_token(refresh_token_plain: str) -> str:
    """
    將 Refresh Token 明文轉成雜湊字串（資料庫只存這個）
    """
    return hashlib.sha256(refresh_token_plain.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> Tuple[datetime, int]:
    """
    回傳：(expires_at_utc, expires_in_seconds)
    """
    expires_at = utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expires_in = int(expires_at.timestamp() - time.time())
    return expires_at, expires_in
