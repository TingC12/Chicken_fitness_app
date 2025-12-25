# app/routers/challenges.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.db import get_db
from app.core.deps import get_current_user_id
from app.models.user import User
from app.services.challenges import get_or_create_this_week_challenge
from app.services.chicken_status import get_weekly_activity_count

from pydantic import BaseModel
from typing import Optional


router = APIRouter(prefix="/challenges", tags=["challenges"])


class WeeklyChallengeRow(BaseModel):
    week_start: str
    title: str
    description: Optional[str]
    condition_type: str
    condition_value: int

    target_count: int
    current_count: int
    reward_coins: int
    reward_exp: int
    completed: bool
    completed_at: Optional[datetime]


@router.get("/weekly", response_model=WeeklyChallengeRow)
def get_weekly_challenge(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # 撈 user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 取得或建立本週挑戰
    wc = get_or_create_this_week_challenge(db, user)

    # 本週目前活動次數
    current_count = get_weekly_activity_count(db, user_id)

    return WeeklyChallengeRow(
        week_start=str(wc.week_start),
        title=wc.title,
        description=wc.description,
        condition_type=wc.condition_type,
        condition_value=wc.condition_value,
        target_count=wc.target_count,
        current_count=current_count,
        reward_coins=wc.reward_coins,
        reward_exp=wc.reward_exp,
        completed=(wc.completed_at is not None),
        completed_at=wc.completed_at,
    )
