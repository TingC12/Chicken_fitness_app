# app/routers/auth_refresh.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from starlette import status

from app.core.db import get_db
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User

router = APIRouter(tags=["auth"])

class RefreshIn(BaseModel):
    refresh_token: str

class RefreshOut(BaseModel):
    access_token: str
    access_token_expires_in: int
    refresh_token: str
    refresh_token_expires_in: int

@router.post("/refresh", response_model=RefreshOut)
def refresh_token(payload: RefreshIn, request: Request, db: Session = Depends(get_db)):
    # 和你原本寫法一致：用 naive 來比（避免 aware/naive 比較噴錯）
    now = datetime.utcnow()

    old_hash = hash_refresh_token(payload.refresh_token)

    old_rt = db.query(RefreshToken).filter(
        RefreshToken.token_hash == old_hash
    ).first()

    if not old_rt or old_rt.revoked_at or old_rt.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # 1) 查 user.status，決定 is_guest
    user = db.query(User).filter(User.id == old_rt.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    is_guest = (user.status == "guest")

    # 2) 先撤銷舊 RT（rotation）
    old_rt.revoked_at = now
    db.commit()

    # 3) 建立新 RT（明文只回一次；DB 存 hash）
    new_rt_plain = generate_refresh_token()
    new_rt_hash = hash_refresh_token(new_rt_plain)
    new_expires_at, new_expires_in = refresh_token_expiry()

    created_ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:255]

    new_rt = RefreshToken(
        user_id=int(user.id),
        token_hash=new_rt_hash,
        expires_at=new_expires_at,
        revoked_at=None,
        created_at=now,
        created_ip=created_ip,
        created_user_agent=ua,
    )
    db.add(new_rt)
    db.commit()

    # 4) 發新 AT（依 status 決定 guest/user）
    at, at_expires_in, _ = create_access_token(user_id=int(user.id), is_guest=is_guest)

    return RefreshOut(
        access_token=at,
        access_token_expires_in=at_expires_in,
        refresh_token=new_rt_plain,
        refresh_token_expires_in=new_expires_in,
    )
