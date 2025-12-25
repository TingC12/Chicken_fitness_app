# path: app/routers/runs.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from random import randint
from app.core.db import get_db
from app.core.deps import get_current_user_id
from app.models.economy import Run, RunStatus
from app.schemas.economy import RunSummaryIn, RunSummaryOut, RunRow
from app.services.ledger import add_ledger_entry
from app.models.user import User
from app.services.level import apply_exp_and_update
from app.services.chicken_status import (
    get_weekly_activity_count,
    calc_chicken_status,
    chicken_exp_multiplier,
)
from app.services.achievements import check_and_unlock_achievements
from app.services.challenges import check_weekly_challenge

router = APIRouter(prefix="/runs", tags=["runs"])
MAX_VALID_SPEED = 20.0  # km/h

@router.post("/summary", response_model=RunSummaryOut)
def runs_summary(payload: RunSummaryIn, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if float(payload.max_speed_kmh) > MAX_VALID_SPEED:
        row = Run(
            user_id=user_id,
            distance_km=payload.distance_km,
            duration_sec=payload.duration_sec,
            max_speed_kmh=payload.max_speed_kmh,
            status=RunStatus.rejected,
            reason="OVERSPEED",
            created_at=datetime.utcnow()
        )
        db.add(row)
        db.commit()
        return RunSummaryOut(coins_awarded=0, status=row.status)

    random_unit = randint(25, 50)
    coins = int(float(payload.distance_km) * random_unit)

    row = Run(
        user_id=user_id,
        distance_km=payload.distance_km,
        duration_sec=payload.duration_sec,
        max_speed_kmh=payload.max_speed_kmh,
        status=RunStatus.awarded,
        coins_awarded=coins,
        created_at=datetime.utcnow()
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    add_ledger_entry(
        db=db, user_id=user_id, delta=coins,
        source="run", ref_id=row.id, idempotency_key=f"run:{row.id}"
    )
    # ✅ 跑步給 EXP（只有真的有發幣時才給）
    if coins > 0:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            # 👉「基礎 EXP」公式：這裡示範用金幣的 1/10，可自行微調
            base_exp = max(1, coins // 10)

            # 依照本週運動次數算出狀態 & 倍率
            weekly_count = get_weekly_activity_count(db, user_id)
            status = calc_chicken_status(db, user_id)       # "weak" / "normal" / "strong"
            multiplier = chicken_exp_multiplier(status)      # 0.5 / 1.0 / 1.5

            # 乘上倍率後的實際 EXP
            exp_gain = int(base_exp * multiplier)
            apply_exp_and_update(user, exp_gain)
            db.commit()
            
            # 🔹 新增：週挑戰 & 成就
            check_weekly_challenge(db, user)
            check_and_unlock_achievements(db, user)
            
    return RunSummaryOut(coins_awarded=coins, status=row.status)

@router.get("/history", response_model=list[RunRow])
def runs_history(limit: int = 50, offset: int = 0, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    rows = db.query(Run).filter(Run.user_id == user_id).order_by(Run.id.desc()).offset(offset).limit(limit).all()
    return [
        RunRow(
            id=r.id, distance_km=float(r.distance_km), duration_sec=r.duration_sec,
            max_speed_kmh=float(r.max_speed_kmh), coins_awarded=r.coins_awarded,
            status=r.status, reason=r.reason, created_at=r.created_at
        ) for r in rows
    ]
