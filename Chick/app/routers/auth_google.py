# app/routers/auth_google.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette import status
from datetime import datetime

from app.core.db import get_db
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.core.config import settings

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

# 你可以放在 app/core/config.py 用 settings 管
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
if not GOOGLE_CLIENT_ID:
    raise RuntimeError("Missing GOOGLE_CLIENT_ID in env")

router = APIRouter(tags=["auth"])


class GoogleAuthIn(BaseModel):
    id_token: str = Field(..., min_length=20)
    device_id: str | None = Field(None, max_length=64)


class GoogleAuthOut(BaseModel):
    user_id: int
    access_token: str
    expires_in: int
    is_guest: bool
    refresh_token: str
    refresh_expires_in: int


def verify_google_token(token: str) -> dict:
    """
    驗證 Google ID Token，成功回傳 claims（含 sub/email）。
    """
    try:
        info = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google id_token",
        )
    # 可再加強：要求 email_verified
    if not info.get("email"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token missing email",
        )
    if info.get("email_verified") is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google email not verified",
        )
    if not info.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token missing sub",
        )
    return info


@router.post("/auth/google", response_model=GoogleAuthOut)
def google_auth(payload: GoogleAuthIn, request: Request, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    info = verify_google_token(payload.id_token)

    google_sub = str(info["sub"])
    email = str(info["email"]).lower().strip()

    # 1) 先看是否已綁定（用 sub 最準）
    user = db.query(User).filter(User.google_sub == google_sub).first()

    if user is None:
        # 2) 如果帶 device_id，嘗試把 guest 升級綁定（保留原資料）
        if payload.device_id:
            guest = db.query(User).filter(
                User.device_id == payload.device_id,
                User.status == "guest",
            ).first()

            if guest:
                # 若 email 已被另一個帳號使用（例如別人先用 email 註冊），避免合併錯帳
                email_owner = db.query(User).filter(
                    User.email == email,
                    User.id != guest.id,
                ).first()
                if email_owner and email_owner.google_sub != google_sub:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Email already in use by another account",
                    )

                guest.google_sub = google_sub
                guest.email = email
                guest.status = "user"
                guest.auth_provider = "google"
                guest.last_login_at = now
                user = guest
            else:
                # device_id 找不到對應 guest，就建立新 user
                user = User(
                    status="user",
                    auth_provider="google",
                    google_sub=google_sub,
                    email=email,
                    device_id=payload.device_id,
                    created_at=now,
                    last_login_at=now,
                )
                db.add(user)
        else:
            # 沒帶 device_id：直接建立新 user
            user = User(
                status="user",
                auth_provider="google",
                google_sub=google_sub,
                email=email,
                created_at=now,
                last_login_at=now,
            )
            db.add(user)

        db.commit()
        db.refresh(user)
    else:
        # 已綁定：更新登入時間/補 email
        user.last_login_at = now
        if not user.email:
            user.email = email
        if user.status != "user":
            user.status = "user"
        if user.auth_provider != "google":
            user.auth_provider = "google"
        db.commit()
        db.refresh(user)

    # 3) 發 Access Token（is_guest=False）
    access_token, expires_in, _ = create_access_token(user_id=int(user.id), is_guest=False)

    # 4) 發 Refresh Token（明文回一次；DB 存 hash）
    rt_plain = generate_refresh_token()
    rt_hash = hash_refresh_token(rt_plain)
    rt_expires_at, rt_expires_in = refresh_token_expiry()

    created_ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:255]

    rt_row = RefreshToken(
        user_id=int(user.id),
        token_hash=rt_hash,
        expires_at=rt_expires_at,
        revoked_at=None,
        created_at=now,
        created_ip=created_ip,
        created_user_agent=ua,
    )
    db.add(rt_row)
    db.commit()

    return GoogleAuthOut(
        user_id=int(user.id),
        access_token=access_token,
        expires_in=expires_in,
        is_guest=False,
        refresh_token=rt_plain,
        refresh_expires_in=rt_expires_in,
    )
