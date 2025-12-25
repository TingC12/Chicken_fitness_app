from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime
from starlette import status

from app.core.db import get_db
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)
from app.models.user import User
from app.models.refresh_token import RefreshToken

router = APIRouter(tags=["auth"])

class GuestIn(BaseModel):
    platform: str = Field(..., max_length=32)
    app_version: str = Field(..., max_length=32)
    device_id: str | None = Field(None, max_length=64)

class GuestOut(BaseModel):
    user_id: int
    access_token: str
    expires_in: int
    is_guest: bool
    refresh_token: str
    refresh_expires_in: int

@router.post("/guest", response_model=GuestOut)
def guest_login(payload: GuestIn, request: Request, db: Session = Depends(get_db)):
    now = datetime.utcnow()

    # 1) 依 device_id 找既有 user，或建立新 user
    user: User | None = None
    if payload.device_id:
        user = db.query(User).filter(User.device_id == payload.device_id).first()

    if user is None:
        user = User(
            status="guest",
            created_at=now,
            last_login_at=now,
            email=None,
            password_hash=None,
            device_id=payload.device_id,
        )
        db.add(user)
        # 確保 user.id 取得
        db.flush()           # 發出 INSERT，取得自增 id
        db.refresh(user)     # 重新載入 -> user.id 一定有值
        db.commit()
    else:
        user.last_login_at = now
        db.commit()
        db.refresh(user)     # 讓 user 欄位最新（保險）

    if not user.id:
        # 若仍然拿不到 id，回報錯誤方便你檢查 model/migration
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Create/Load user failed: missing user.id"
        )

    # 2) 簽 Access Token
    access_token, expires_in, _ = create_access_token(user_id=int(user.id), is_guest=True)

    # 3) 產生 Refresh Token（明文只回一次；DB 存 hash）
    rt_plain = generate_refresh_token()
    rt_hash  = hash_refresh_token(rt_plain)
    rt_expires_at, rt_expires_in = refresh_token_expiry()

    created_ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:255]

    r = RefreshToken(
        user_id=int(user.id),
        token_hash=rt_hash,
        expires_at=rt_expires_at,
        revoked_at=None,
        created_at=now,
        created_ip=created_ip,
        created_user_agent=ua,
    )
    db.add(r)
    db.commit()

    return GuestOut(
        user_id=int(user.id),
        access_token=access_token,
        expires_in=expires_in,
        is_guest=True,
        refresh_token=rt_plain,
        refresh_expires_in=rt_expires_in,
    )
