# path: app/routers/trainings.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date
from decimal import Decimal

from app.core.db import get_db
from app.core.deps import get_current_user_id
from app.models.economy import TrainingLog
from app.schemas.economy import (
    TrainingLogCreate, TrainingLogRow,
    TrainingStatsOut, TrainingStatsPoint,
)

router = APIRouter(prefix="/trainings", tags=["trainings"])

@router.post("/logs", response_model=TrainingLogRow)
def create_training_log(
    payload: TrainingLogCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # 處理時間：不填就用現在
    now = datetime.utcnow()
    performed_at = payload.performed_at or now

    # weight_kg 是 Decimal，要轉成 float 再算 volume
    weight = float(payload.weight_kg)
    volume = int(weight * payload.reps * payload.sets)

    row = TrainingLog(
        user_id=user_id,
        exercise_name=payload.exercise_name,
        weight_kg=payload.weight_kg,
        reps=payload.reps,
        sets=payload.sets,
        volume=volume,
        performed_at=performed_at,
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return TrainingLogRow(
        id=row.id,
        exercise_name=row.exercise_name,
        weight_kg=float(row.weight_kg),
        reps=row.reps,
        sets=row.sets,
        volume=row.volume,
        performed_at=row.performed_at,
    )

@router.get("/logs/history", response_model=list[TrainingLogRow])
def training_logs_history(
    limit: int = 50,
    offset: int = 0,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(TrainingLog)
        .filter(TrainingLog.user_id == user_id)
        .order_by(TrainingLog.performed_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        TrainingLogRow(
            id=r.id,
            exercise_name=r.exercise_name,
            weight_kg=float(r.weight_kg),
            reps=r.reps,
            sets=r.sets,
            volume=r.volume,
            performed_at=r.performed_at,
        )
        for r in rows
    ]

@router.get("/stats", response_model=TrainingStatsOut)
def training_stats(
    range: str = "week",
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if range not in ("week", "month"):
        raise HTTPException(status_code=400, detail="range must be 'week' or 'month'")

    today = datetime.utcnow().date()

    if range == "week":
        days = 6   # 今天 + 前 6 天 = 7 天
    else:
        days = 29  # 今天 + 前 29 天 = 30 天

    start_date = today - timedelta(days=days)

    # 用 MySQL 的 DATE() 把 datetime 壓成日期來 group by
    date_expr = func.date(TrainingLog.performed_at)

    rows = (
        db.query(
            date_expr.label("d"),
            func.coalesce(func.sum(TrainingLog.volume), 0).label("total_volume"),
            func.coalesce(func.sum(TrainingLog.sets), 0).label("total_sets"),
        )
        .filter(
            TrainingLog.user_id == user_id,
            TrainingLog.performed_at >= start_date,
        )
        .group_by(date_expr)
        .order_by(date_expr)
        .all()
    )

    points: list[TrainingStatsPoint] = [
        TrainingStatsPoint(
            date=row.d,
            total_volume=int(row.total_volume or 0),
            total_sets=int(row.total_sets or 0),
        )
        for row in rows
    ]

    return TrainingStatsOut(range=range, points=points)
