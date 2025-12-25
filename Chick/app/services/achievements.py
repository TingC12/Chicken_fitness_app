from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.economy import (
    Achievement, UserAchievement,
    Checkin, CheckinStatus, Run, RunStatus,
)
from app.models.user import User
from app.services.ledger import add_ledger_entry
from app.services.level import apply_exp_and_update
from app.services.chicken_status import get_all_activity_dates, calc_current_streak

def _get_basic_stats(db: Session, user_id: int) -> dict:
    total_checkins = (
        db.query(func.count(Checkin.id))
        .filter(
            Checkin.user_id == user_id,
            Checkin.status.in_([CheckinStatus.verified, CheckinStatus.awarded]),
        )
        .scalar() or 0
    )
    total_runs = (
        db.query(func.count(Run.id))
        .filter(
            Run.user_id == user_id,
            Run.status == RunStatus.awarded,
        )
        .scalar() or 0
    )
    dates = get_all_activity_dates(db, user_id)
    current_streak = calc_current_streak(dates)

    return {
        "total_checkins": total_checkins,
        "total_runs": total_runs,
        "streak": current_streak,
    }


def check_and_unlock_achievements(db: Session, user: User) -> list[UserAchievement]:
    """
    在「有新活動」後呼叫：
      - 打卡成功
      - 跑步成功
      - 升級 / 吃道具後
    """
    stats = _get_basic_stats(db, user.id)

    # 目前已解鎖的成就 id
    unlocked_ids = {
        ua.achievement_id
        for ua in db.query(UserAchievement).filter(UserAchievement.user_id == user.id).all()
    }

    new_unlocked: list[UserAchievement] = []

    # 撈所有成就定義
    all_ach = db.query(Achievement).all()

    for ach in all_ach:
        if ach.id in unlocked_ids:
            continue

        ok = False
        if ach.condition_type == "total_checkins":
            ok = stats["total_checkins"] >= ach.condition_value
        elif ach.condition_type == "total_runs":
            ok = stats["total_runs"] >= ach.condition_value
        elif ach.condition_type == "streak":
            ok = stats["streak"] >= ach.condition_value
        elif ach.condition_type == "level":
            ok = (user.level or 1) >= ach.condition_value

        if not ok:
            continue

        ua = UserAchievement(
            user_id=user.id,
            achievement_id=ach.id,
            unlocked_at=datetime.utcnow(),
        )
        db.add(ua)
        new_unlocked.append(ua)

        # 發獎勵：coins + exp
        if ach.reward_coins != 0:
            add_ledger_entry(
                db=db,
                user_id=user.id,
                delta=ach.reward_coins,
                source="achievement",
                ref_id=ach.id,
                idempotency_key=f"achievement:{user.id}:{ach.id}",
            )
        if ach.reward_exp != 0:
            apply_exp_and_update(user, ach.reward_exp)

    if new_unlocked:
        db.commit()

    return new_unlocked
