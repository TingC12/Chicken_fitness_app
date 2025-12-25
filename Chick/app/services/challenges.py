# app/services/challenges.py

from datetime import datetime
from sqlalchemy.orm import Session

from app.models.economy import WeeklyChallenge
from app.services.chicken_status import get_week_range_utc, get_weekly_activity_count
from app.services.ledger import add_ledger_entry
from app.services.level import apply_exp_and_update
from app.models.user import User


def get_or_create_this_week_challenge(db: Session, user: User) -> WeeklyChallenge:
    week_start, _ = get_week_range_utc()
    ws_date = week_start.date()

    row = (
        db.query(WeeklyChallenge)
        .filter(
            WeeklyChallenge.user_id == user.id,
            WeeklyChallenge.week_start == ws_date,
        )
        .first()
    )
    if row:
        return row

    # ✅ 避免 target_count / condition_value 未來不一致
    target = 3

    row = WeeklyChallenge(
        user_id=user.id,
        week_start=ws_date,

        # 任務文案 + 條件
        title="本週挑戰：運動達標",
        description="本週累積完成 3 次運動（打卡或跑步都算）",
        condition_type="weekly_activity_count",
        condition_value=target,

        # 相容舊欄位（但要同步）
        target_count=target,
        reward_coins=50,
        reward_exp=100,
    )

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def check_weekly_challenge(db: Session, user: User) -> WeeklyChallenge:
    """
    在每次運動成功（打卡 or 跑步）後呼叫。
    如果達成條件而且尚未完成，就發獎勵。
    """
    wc = get_or_create_this_week_challenge(db, user)
    if wc.completed_at is not None:
        return wc

    # === 計算進度 / 判斷是否達成 ===
    if wc.condition_type == "weekly_activity_count":
        count = get_weekly_activity_count(db, user.id)
        goal = wc.condition_value
        if count < goal:
            return wc
    else:
        # 先保留：未來擴充其它規則
        return wc

    # === 達成：標記完成 + 發獎（一次 commit）===
    wc.completed_at = datetime.utcnow()

    # Coins：用 ledger 防重複
    if wc.reward_coins:
        add_ledger_entry(
            db=db,
            user_id=user.id,
            delta=wc.reward_coins,
            source="weekly_challenge",
            ref_id=wc.id,
            idempotency_key=f"weekly_challenge:{user.id}:{wc.week_start.isoformat()}",
        )

    # EXP：修正正確呼叫方式
    if wc.reward_exp:
        apply_exp_and_update(user, wc.reward_exp)

    db.commit()
    db.refresh(wc)
    return wc
