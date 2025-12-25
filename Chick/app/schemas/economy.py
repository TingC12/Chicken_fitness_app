# path: app/schemas/economy.py
from pydantic import BaseModel, Field, condecimal
from typing import Optional, Literal
from datetime import datetime, date
from app.models.economy import CheckinStatus, RunStatus

# /me
class MeSummary(BaseModel):
    user_id: int
    status: Literal["guest","user","admin"] = "guest"
    coins: int
    today_checkin_status: Literal["none","started","verified","awarded"]
    last_login_at: Optional[datetime] = None
    
    # 🔹 新增：小雞名字（可以是 None）
    chicken_name: Optional[str] = None
    
    # 🔹 新增：養成相關
    exp: int
    level: int
    
    # 🔹 新增：這一級的進度
    exp_in_current_level: int         # 我這一級目前有多少 EXP（分子）
    exp_for_next_level: int           # 這一級需要多少 EXP 才能升級（分母）
    exp_remaining_to_next_level: int  # 還差多少 EXP 才能升級

    chicken_status: Literal["weak", "normal", "strong"]
    weekly_activity_count: int  # 可有可無，但很實用（前端也能顯示「本週已運動 X 次」）
    
    # 🔹 新增：目前連續運動天數
    current_streak: int

# 打卡
class CheckinStartIn(BaseModel):
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)

class CheckinStartOut(BaseModel):
    checkin_id: int
    status: CheckinStatus
    started_at: datetime

class CheckinHeartbeatIn(BaseModel):
    checkin_id: int

class CheckinEndIn(BaseModel):
    checkin_id: int
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)

class CheckinEndOut(BaseModel):
    verified: bool
    dwell_minutes: int
    coins_awarded: int

# 👇 在這裡加一個 debug 用的輸入模型
class CheckinRewindStartIn(BaseModel):
    checkin_id: int
    # 往回調幾分鐘（上限先隨便抓個一天 1440 分鐘，避免亂炸）
    rewind_minutes: int = Field(..., ge=0, le=3000)
    
class CheckinRow(BaseModel):
    id: int
    status: CheckinStatus
    dwell_minutes: Optional[int]
    coins_awarded: int
    reason: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]

# 跑步
class RunSummaryIn(BaseModel):
    distance_km: condecimal(gt=0, max_digits=6, decimal_places=3)
    duration_sec: int = Field(..., gt=0)
    max_speed_kmh: condecimal(gt=0, max_digits=5, decimal_places=2)

class RunSummaryOut(BaseModel):
    coins_awarded: int
    status: RunStatus

class RunRow(BaseModel):
    id: int
    distance_km: float
    duration_sec: int
    max_speed_kmh: float
    coins_awarded: int
    status: RunStatus
    reason: Optional[str]
    created_at: datetime


# ============================
# 訓練課表 / 紀錄
# ============================

class TrainingLogCreate(BaseModel):
    exercise_name: str = Field(..., max_length=64)
    weight_kg: condecimal(max_digits=5, decimal_places=2, gt=0)
    reps: int = Field(..., ge=1, le=1000)
    sets: int = Field(..., ge=1, le=100)
    performed_at: Optional[datetime] = None  # 不填就用後端現在時間

class TrainingLogRow(BaseModel):
    id: int
    exercise_name: str
    weight_kg: float
    reps: int
    sets: int
    volume: int
    performed_at: datetime

class TrainingStatsPoint(BaseModel):
    date: date
    total_volume: int
    total_sets: int

class TrainingStatsOut(BaseModel):
    range: Literal["week", "month"]
    points: list[TrainingStatsPoint]


# ============================
# 自訂訓練計畫（菜單）
# ============================

class TrainingPlanItemIn(BaseModel):
    date: date
    exercise_name: str = Field(..., max_length=64)
    target_sets: int = Field(..., ge=1, le=100)
    target_reps: int = Field(..., ge=1, le=1000)
    target_weight_kg: Optional[condecimal(max_digits=5, decimal_places=2, gt=0)] = None
    note: Optional[str] = Field(None, max_length=255)
    order_index: Optional[int] = Field(None, ge=0, le=1000)

class TrainingPlanItemCreateIn(BaseModel):
    date: date
    exercise_name: str = Field(..., max_length=64)
    target_sets: int = Field(..., ge=1, le=100)
    target_reps: int = Field(..., ge=1, le=1000)
    target_weight_kg: Optional[condecimal(max_digits=5, decimal_places=2, gt=0)] = None
    note: Optional[str] = Field(None, max_length=255)
    order_index: Optional[int] = Field(None, ge=0, le=1000)  # 不給就自動排到最後

class TrainingPlanItemPatchIn(BaseModel):
    exercise_name: Optional[str] = Field(None, max_length=64)
    target_sets: Optional[int] = Field(None, ge=1, le=100)
    target_reps: Optional[int] = Field(None, ge=1, le=1000)
    target_weight_kg: Optional[condecimal(max_digits=5, decimal_places=2, gt=0)] = None
    note: Optional[str] = Field(None, max_length=255)
    order_index: Optional[int] = Field(None, ge=0, le=1000)
    
class TrainingPlanDayUpsertIn(BaseModel):
    """
    建立 / 覆蓋「某一天」的訓練計畫。
    - date：那一天
    - items：該天的所有訓練項目
    """
    date: date
    items: list[TrainingPlanItemIn]


class TrainingPlanItemRow(BaseModel):
    id: int
    exercise_name: str
    target_sets: int
    target_reps: int
    target_weight_kg: Optional[float] = None
    note: Optional[str] = None
    order_index: int


class TrainingPlanDayOut(BaseModel):
    date: date
    items: list[TrainingPlanItemRow]


class TrainingPlanWeekOut(BaseModel):
    start_date: date
    end_date: date
    days: list[TrainingPlanDayOut]


class TrainingPlanCopyFromLastWeekIn(BaseModel):
    """
    複製上一週「同一天」的訓練計畫：
    - 例如 date=2025-12-15，就會去找 2025-12-08 的計畫來複製。
    """
    date: date

  
# --- 商店商品 ---
class StoreItemRow(BaseModel):
    id: int
    name: str
    price_coins: int
    exp_min: int
    exp_max: int
    description: Optional[str] = None

# --- 買道具 ---
class PurchaseCreate(BaseModel):
    item_id: int

class PurchaseResult(BaseModel):
    item_id: int
    item_name: str
    coins_spent: int
    coins_after: int

# --- 背包 ---
class InventoryItemRow(BaseModel):
    item_id: int
    name: str
    quantity: int
    description: Optional[str] = None

# --- 使用道具 ---
class UseItemIn(BaseModel):
    item_id: int

class UseItemResult(BaseModel):
    item_id: int
    item_name: str
    exp_gain: int
    new_exp: int
    new_level: int
    remaining_quantity: int