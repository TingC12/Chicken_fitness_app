# app/repos/tokens_repo.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.refresh_token import RefreshToken

async def add_refresh_token(
    db: AsyncSession,
    *,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
    created_ip: str | None,
    created_user_agent: str | None,
) -> RefreshToken:
    """
    新增一筆 RT（只存雜湊，不存明文）
    """
    rt = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_ip=created_ip,
        created_user_agent=created_user_agent,
    )
    db.add(rt)
    await db.flush()
    return rt

async def find_rt_by_hash(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash).limit(1)
    res = await db.execute(stmt)
    return res.scalars().first()

async def revoke_rt_by_id(db: AsyncSession, rt_id: int, *, revoked_at: datetime) -> None:
    stmt = (
        update(RefreshToken)
        .where(RefreshToken.id == rt_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )
    await db.execute(stmt)

async def revoke_all_rts_for_user(db: AsyncSession, user_id: int, *, revoked_at: datetime) -> int:
    """
    撤銷該 user 目前所有有效 RT，回傳影響筆數
    """
    stmt = (
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )
    res = await db.execute(stmt)
    return res.rowcount or 0
