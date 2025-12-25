# app/services/chicken_status.py
from __future__ import annotations

from datetime import datetime, timedelta, date
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.economy import Checkin, CheckinStatus, Run, RunStatus


# ========================
#  Week range / weekly count
# ========================

def get_week_range_utc() -> tuple[datetime, datetime]:
    """
    回傳本週區間 [週一 00:00, 下週一 00:00)，使用 UTC。
    """
    today = datetime.utcnow().date()
    monday = today - timedelta(days=today.weekday())  # Monday=0 ... Sunday=6
    week_start = datetime(monday.year, monday.month, monday.day)
    week_end = week_start + timedelta(days=7)
    return week_start, week_end


def _valid_checkin_statuses() -> list[CheckinStatus]:
    """
    有些專案版本的 CheckinStatus 可能沒有 awarded / rejected，
    這裡做相容性處理：至少包含 verified，若有 awarded 就一起算有效打卡。
    """
    statuses: list[CheckinStatus] = [CheckinStatus.verified]
    try:
        statuses.append(CheckinStatus.awarded)  # type: ignore[attr-defined]
    except Exception:
        pass
    return statuses


def get_weekly_activity_count(db: Session, user_id: int) -> int:
    """
    計算本週運動次數（UTC 週一～下週一）：
    - 有效打卡：status in [verified, (awarded 若存在)]
    - 有效跑步：status = awarded（依你的 RunStatus 設計）
    """
    week_start, week_end = get_week_range_utc()

    # 打卡次數
    checkin_count = (
        db.query(Checkin)
        .filter(
            Checkin.user_id == user_id,
            Checkin.status.in_(_valid_checkin_statuses()),
            Checkin.started_at >= week_start,
            Checkin.started_at < week_end,
        )
        .count()
    )

    # 跑步次數（若你的跑步成功狀態不是 awarded，改這裡就好）
    run_count = (
        db.query(Run)
        .filter(
            Run.user_id == user_id,
            Run.status == RunStatus.awarded,
            Run.created_at >= week_start,
            Run.created_at < week_end,
        )
        .count()
    )

    return checkin_count + run_count


# ========================
#  🐣 Chicken status v2 (你要的邏輯)
# ========================

WEAK_AFTER_DAYS = 4        # 5 天沒運動才 weak
STRONG_WEEKLY_COUNT = 3    # 本週 >= 5 次才 strong


def get_last_activity_at(db: Session, user_id: int) -> datetime | None:
    """
    取得「最近一次運動時間」（UTC）：
    - 打卡：取 ended_at 最大值（status=有效打卡，且 ended_at 不為 None）
    - 跑步：取 created_at 最大值（status=awarded）

    若你之後要把 training logs 也算運動，把它加進 candidates 即可。
    """
    last_checkin = (
        db.query(func.max(Checkin.ended_at))
        .filter(
            Checkin.user_id == user_id,
            Checkin.status.in_(_valid_checkin_statuses()),
            Checkin.ended_at.isnot(None),
        )
        .scalar()
    )

    last_run = (
        db.query(func.max(Run.created_at))
        .filter(
            Run.user_id == user_id,
            Run.status == RunStatus.awarded,
        )
        .scalar()
    )

    candidates = [t for t in [last_checkin, last_run] if t is not None]
    return max(candidates) if candidates else None


def calc_chicken_status(db: Session, user_id: int) -> str:
    """
    你要的新規則（v2）：
    1) 新用戶/完全沒運動紀錄：normal
    2) 距離最近一次運動 >= 5 天：weak
    3) 最近 5 天內有運動：
       - 本週運動次數 >= 5：strong
       - 否則：normal
    """
    now = datetime.utcnow()

    last_activity_at = get_last_activity_at(db, user_id)
    if last_activity_at is None:
        return "normal"

    days_since = (now.date() - last_activity_at.date()).days
    if days_since >= WEAK_AFTER_DAYS:
        return "weak"

    weekly_count = get_weekly_activity_count(db, user_id)
    if weekly_count >= STRONG_WEEKLY_COUNT:
        return "strong"

    return "normal"


def chicken_exp_multiplier(status: str) -> float:
    """
    套用在 EXP 計算上的倍率：
    - weak   → 0.5
    - normal → 1.0
    - strong → 1.5
    """
    if status == "weak":
        return 0.5
    if status == "strong":
        return 1.5
    return 1.0


# ========================
#  🔥 Streak 用的新工具
# ========================

def get_all_activity_dates(db: Session, user_id: int) -> set[date]:
    """
    回傳該使用者「有運動」的所有日期集合（UTC 的日期）
    - 有效打卡：status in [verified, (awarded 若存在)] → 使用 started_at.date()
    - 有效跑步：status = awarded → 使用 created_at.date()
    """
    q1 = (
        db.query(Checkin.started_at)
        .filter(
            Checkin.user_id == user_id,
            Checkin.status.in_(_valid_checkin_statuses()),
        )
        .all()
    )
    q2 = (
        db.query(Run.created_at)
        .filter(
            Run.user_id == user_id,
            Run.status == RunStatus.awarded,
        )
        .all()
    )

    dates: set[date] = set()
    for (dt,) in q1:
        if dt:
            dates.add(dt.date())
    for (dt,) in q2:
        if dt:
            dates.add(dt.date())
    return dates


def calc_current_streak(activity_dates: set[date]) -> int:
    """
    計算「從今天往回算」的連續運動天數。
    例如今天有運動、昨天有、前天沒 → streak = 2
    """
    if not activity_dates:
        return 0

    today = datetime.utcnow().date()
    streak = 0
    cur = today

    while cur in activity_dates:
        streak += 1
        cur = cur - timedelta(days=1)

    return streak
