# app/routers/achievements.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.db import get_db
from app.core.deps import get_current_user_id
from app.models.economy import Achievement, UserAchievement

from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/achievements", tags=["achievements"])

class AchievementRow(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str]
    unlocked: bool
    unlocked_at: Optional[datetime]

@router.get("/my", response_model=list[AchievementRow])
def my_achievements(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    achs = db.query(Achievement).all()
    ua_map = {
        ua.achievement_id: ua
        for ua in db.query(UserAchievement).filter(UserAchievement.user_id == user_id).all()
    }

    result: list[AchievementRow] = []
    for a in achs:
        ua = ua_map.get(a.id)
        result.append(
            AchievementRow(
                id=a.id,
                code=a.code,
                name=a.name,
                description=a.description,
                unlocked=ua is not None,
                unlocked_at=ua.unlocked_at if ua else None,
            )
        )
    return result
