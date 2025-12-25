# path: app/models/economy.py
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, Enum, DECIMAL, Index, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from datetime import datetime
from app.core.db import Base
from app.models.user import utcnow_naive  # 直接重用
from sqlalchemy import BigInteger, ForeignKey

class CheckinStatus(str, enum.Enum):
    started = "started"
    ended = "ended"
    verified = "verified"
    rejected = "rejected"
    awarded = "awarded"

class RunStatus(str, enum.Enum):
    submitted = "submitted"
    rejected = "rejected"
    awarded = "awarded"

class CoinsLedger(Base):
    __tablename__ = "coins_ledger"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger,ForeignKey("users.id", ondelete="CASCADE"),nullable=False,index=True,)
    delta = Column(Integer, nullable=False)
    source = Column(String(32), nullable=False)
    ref_id = Column(BigInteger, nullable=True)
    idempotency_key = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (Index("idx_coins_user_created", "user_id", "created_at"),)

class Checkin(Base):
    __tablename__ = "checkins"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger,ForeignKey("users.id", ondelete="CASCADE"),nullable=False,index=True,)
    
     # ✅ 新增：這次打卡對應的健身房（可為 NULL）
    gym_id = Column(Integer, ForeignKey("gyms.id", ondelete="SET NULL"), nullable=True, index=True)

    start_lat = Column(DECIMAL(9,6), nullable=True)
    start_lng = Column(DECIMAL(9,6), nullable=True)
    end_lat = Column(DECIMAL(9,6), nullable=True)
    end_lng = Column(DECIMAL(9,6), nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    dwell_minutes = Column(Integer, nullable=True)
    coins_awarded = Column(Integer, nullable=False, default=0)
    # 👇 新增：細緻計算用
    accum_minutes = Column(Integer, nullable=False, default=0)  # 已累積的運動分鐘
    last_tick_at = Column(DateTime, nullable=True)              # 上次累計的時間
    
    status = Column(Enum(CheckinStatus), nullable=False, default=CheckinStatus.started)
    reason = Column(String(128), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    __table_args__ = (Index("idx_checkins_user_created", "user_id", "created_at"),)

    # （可選）如果你之後想直接 row.gym 取健身房資料
    gym = relationship("Gym", lazy="joined")
class Run(Base):
    __tablename__ = "runs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger,ForeignKey("users.id", ondelete="CASCADE"),nullable=False,index=True,)
    distance_km = Column(DECIMAL(6,3), nullable=False)
    duration_sec = Column(Integer, nullable=False)
    max_speed_kmh = Column(DECIMAL(5,2), nullable=False)
    coins_awarded = Column(Integer, nullable=False, default=0)
    status = Column(Enum(RunStatus), nullable=False, default=RunStatus.submitted)
    reason = Column(String(128), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (Index("idx_runs_user_created", "user_id", "created_at"),)

class TrainingLog(Base):
    __tablename__ = "training_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    exercise_name: Mapped[str] = mapped_column(String(64), nullable=False)
    weight_kg: Mapped[float] = mapped_column(DECIMAL(5, 2), nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)

    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow_naive, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow_naive
    )
    
class TrainingPlanItem(Base):
    __tablename__ = "training_plan_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 哪個使用者的菜單
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 這個訓練項目是排在「哪一天」的計畫
    date = Column(Date, nullable=False, index=True)

    # 訓練內容
    exercise_name = Column(String(64), nullable=False)
    target_sets = Column(Integer, nullable=False)
    target_reps = Column(Integer, nullable=False)
    target_weight_kg = Column(DECIMAL(5, 2), nullable=True)  # 可選
    note = Column(String(255), nullable=True)

    # 同一天的顯示順序（0,1,2,...）
    order_index = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_training_plan_user_date", "user_id", "date"),
    )
    
class StoreItem(Base):
    __tablename__ = "store_items"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    price_coins = Column(Integer, nullable=False)
    exp_min = Column(Integer, nullable=False)
    exp_max = Column(Integer, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class InventoryItem(Base):
    __tablename__ = "inventory_items"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(BigInteger, ForeignKey("store_items.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    item = relationship("StoreItem")

class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(BigInteger, ForeignKey("store_items.id", ondelete="CASCADE"), nullable=False, index=True)
    coins_spent = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ItemUsage(Base):
    __tablename__ = "item_usages"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(BigInteger, ForeignKey("store_items.id", ondelete="CASCADE"), nullable=False, index=True)
    exp_gain = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
class Achievement(Base):
    __tablename__ = "achievements"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, unique=True)
    name = Column(String(64), nullable=False)
    description = Column(String(255), nullable=True)
    condition_type = Column(String(32), nullable=False)
    condition_value = Column(Integer, nullable=False)
    reward_coins = Column(Integer, nullable=False, default=0)
    reward_exp = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    achievement_id = Column(BigInteger, ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False, index=True)
    unlocked_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    achievement = relationship("Achievement")

class WeeklyChallenge(Base):
    __tablename__ = "weekly_challenges"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    week_start = Column(Date, nullable=False)
    
    # ✅ 新增
    title = Column(String(64), nullable=False, default="本週挑戰")
    description = Column(String(255), nullable=True)
    condition_type = Column(String(32), nullable=False, default="weekly_activity_count")
    condition_value = Column(Integer, nullable=False, default=3)

    target_count = Column(Integer, nullable=False)
    reward_coins = Column(Integer, nullable=False, default=0)
    reward_exp = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime, nullable=True)
