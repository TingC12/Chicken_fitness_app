# app/repos/users_repo.py
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User

'''
def utcnow():
    return datetime.now(timezone.utc)
'''

async def get_user_by_device_id(db: AsyncSession, device_id: str) -> User | None:
    if not device_id:
        return None
    stmt = select(User).where(User.device_id == device_id).limit(1)
    res = await db.execute(stmt)
    return res.scalars().first()

async def create_guest_user(db: AsyncSession, *, device_id: str | None) -> User:
    """
    建立 guest 使用者（可帶入 device_id；沒有就先 None）
    """
    user = User(status="guest", device_id=device_id, created_at=datetime.utcnow(),  # ✅ naive UTC
)
    db.add(user)
    await db.flush()  # 讓 user.id 取得值
    return user

async def touch_last_login(db: AsyncSession, user_id: int) -> None:
    """
    更新使用者最後登入時間
    """
    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(last_login_at=func.now())  # 也可用 utcnow()
    )
    await db.execute(stmt)
