# app/routers/training_plans.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date as date_type, timedelta, datetime

from app.core.db import get_db
from app.core.deps import get_current_user_id
from app.models.economy import TrainingPlanItem
from app.schemas.economy import (
    TrainingPlanDayUpsertIn,
    TrainingPlanDayOut,
    TrainingPlanItemRow,
    TrainingPlanWeekOut,
    TrainingPlanCopyFromLastWeekIn,
)
from sqlalchemy import func
from app.schemas.economy import TrainingPlanItemCreateIn, TrainingPlanItemPatchIn

router = APIRouter(prefix="/training_plans", tags=["training_plans"])


def _build_day_out(
    *,
    user_id: int,
    target_date: date_type,
    db: Session,
) -> TrainingPlanDayOut:
    rows = (
        db.query(TrainingPlanItem)
        .filter(
            TrainingPlanItem.user_id == user_id,
            TrainingPlanItem.date == target_date,
        )
        .order_by(TrainingPlanItem.order_index.asc(), TrainingPlanItem.id.asc())
        .all()
    )

    items: list[TrainingPlanItemRow] = []
    for r in rows:
        items.append(
            TrainingPlanItemRow(
                id=r.id,
                exercise_name=r.exercise_name,
                target_sets=r.target_sets,
                target_reps=r.target_reps,
                target_weight_kg=float(r.target_weight_kg) if r.target_weight_kg is not None else None,
                note=r.note,
                order_index=r.order_index,
            )
        )

    return TrainingPlanDayOut(date=target_date, items=items)


@router.put("/day", response_model=TrainingPlanDayOut)
def upsert_day_plan(
    payload: TrainingPlanDayUpsertIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    建立 / 覆蓋某一天的訓練計畫：
    - 會先刪掉該 user 在這一天的舊計畫，再用新的覆蓋。
    """
    target_date = payload.date

    # 先刪掉舊的
    (
        db.query(TrainingPlanItem)
        .filter(
            TrainingPlanItem.user_id == user_id,
            TrainingPlanItem.date == target_date,
        )
        .delete()
    )

    # 新增新的 items
    for idx, item in enumerate(payload.items):
        order_idx = item.order_index if item.order_index is not None else idx

        row = TrainingPlanItem(
            user_id=user_id,
            # 這裡強制使用 payload.date，避免 item.date 傳錯日
            date=target_date,
            exercise_name=item.exercise_name,
            target_sets=item.target_sets,
            target_reps=item.target_reps,
            target_weight_kg=item.target_weight_kg,
            note=item.note,
            order_index=order_idx,
            created_at=datetime.utcnow(),
        )
        db.add(row)

    db.commit()

    return _build_day_out(user_id=user_id, target_date=target_date, db=db)


@router.get("/day", response_model=TrainingPlanDayOut)
def get_day_plan(
    date: date_type = Query(..., description="要查詢的日期（yyyy-mm-dd）"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    取得某一天的訓練計畫。
    - 若當天沒有任何項目，回傳 items 為空陣列。
    """
    return _build_day_out(user_id=user_id, target_date=date, db=db)


@router.get("/week", response_model=TrainingPlanWeekOut)
def get_week_plan(
    start_date: date_type = Query(..., description="週的起始日期（通常是週一）"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    取得一整週的訓練計畫：
    - start_date + 6 天，總共 7 天。
    """
    end_date = start_date + timedelta(days=6)

    rows = (
        db.query(TrainingPlanItem)
        .filter(
            TrainingPlanItem.user_id == user_id,
            TrainingPlanItem.date >= start_date,
            TrainingPlanItem.date <= end_date,
        )
        .order_by(
            TrainingPlanItem.date.asc(),
            TrainingPlanItem.order_index.asc(),
            TrainingPlanItem.id.asc(),
        )
        .all()
    )

    # 按日期 group
    day_map: dict[date_type, list[TrainingPlanItemRow]] = {}
    for r in rows:
        d = r.date
        arr = day_map.setdefault(d, [])
        arr.append(
            TrainingPlanItemRow(
                id=r.id,
                exercise_name=r.exercise_name,
                target_sets=r.target_sets,
                target_reps=r.target_reps,
                target_weight_kg=float(r.target_weight_kg) if r.target_weight_kg is not None else None,
                note=r.note,
                order_index=r.order_index,
            )
        )

    # 組成 7 天的回傳（沒有計畫的日子也要出現，items 為 []）
    days_out: list[TrainingPlanDayOut] = []
    cur = start_date
    while cur <= end_date:
        items = day_map.get(cur, [])
        days_out.append(TrainingPlanDayOut(date=cur, items=items))
        cur = cur + timedelta(days=1)

    return TrainingPlanWeekOut(
        start_date=start_date,
        end_date=end_date,
        days=days_out,
    )

@router.post("/day/items", response_model=TrainingPlanDayOut)
def add_plan_item(
    payload: TrainingPlanItemCreateIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    新增「單一動作」到某一天（不覆蓋整天）。
    - order_index 不給：自動排在當天最後一個
    - 回傳該天完整 items（方便前端直接刷新）
    """
    target_date = payload.date

    if payload.order_index is None:
        max_idx = (
            db.query(func.coalesce(func.max(TrainingPlanItem.order_index), -1))
            .filter(TrainingPlanItem.user_id == user_id, TrainingPlanItem.date == target_date)
            .scalar()
        )
        order_idx = int(max_idx) + 1
    else:
        order_idx = payload.order_index

    row = TrainingPlanItem(
        user_id=user_id,
        date=target_date,
        exercise_name=payload.exercise_name,
        target_sets=payload.target_sets,
        target_reps=payload.target_reps,
        target_weight_kg=payload.target_weight_kg,
        note=payload.note,
        order_index=order_idx,
        created_at=datetime.utcnow(),
        updated_at=None,
    )
    db.add(row)
    db.commit()

    return _build_day_out(user_id=user_id, target_date=target_date, db=db)


@router.patch("/items/{item_id}", response_model=TrainingPlanDayOut)
def patch_plan_item(
    item_id: int,
    payload: TrainingPlanItemPatchIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    修改單一動作（不影響同一天其他動作）。
    回傳該 item 所在日期的完整 items。
    """
    row = db.query(TrainingPlanItem).filter(
        TrainingPlanItem.id == item_id,
        TrainingPlanItem.user_id == user_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="plan item not found")

    if payload.exercise_name is not None:
        row.exercise_name = payload.exercise_name
    if payload.target_sets is not None:
        row.target_sets = payload.target_sets
    if payload.target_reps is not None:
        row.target_reps = payload.target_reps
    if payload.target_weight_kg is not None:
        row.target_weight_kg = payload.target_weight_kg
    if payload.note is not None:
        row.note = payload.note
    if payload.order_index is not None:
        row.order_index = payload.order_index

    row.updated_at = datetime.utcnow()
    target_date = row.date

    db.commit()
    return _build_day_out(user_id=user_id, target_date=target_date, db=db)

@router.delete("/items/{item_id}", response_model=TrainingPlanDayOut)
def delete_plan_item(
    item_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    刪除單一動作（不影響同一天其他動作）。
    回傳該 item 所在日期的完整 items。
    """
    row = db.query(TrainingPlanItem).filter(
        TrainingPlanItem.id == item_id,
        TrainingPlanItem.user_id == user_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="plan item not found")

    target_date = row.date
    db.delete(row)
    db.commit()

    return _build_day_out(user_id=user_id, target_date=target_date, db=db)

@router.post("/copy_from_last_week", response_model=TrainingPlanDayOut)
def copy_from_last_week(
    payload: TrainingPlanCopyFromLastWeekIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    複製上一週「同一天」的訓練計畫：
    - 例如 payload.date=2025-12-15，就會去找 2025-12-08 的計畫來複製。
    - 會覆蓋目標日期原本的計畫。
    """
    target_date = payload.date
    source_date = target_date - timedelta(days=7)

    source_rows = (
        db.query(TrainingPlanItem)
        .filter(
            TrainingPlanItem.user_id == user_id,
            TrainingPlanItem.date == source_date,
        )
        .order_by(TrainingPlanItem.order_index.asc(), TrainingPlanItem.id.asc())
        .all()
    )

    if not source_rows:
        raise HTTPException(
            status_code=404,
            detail=f"no training plan found for last week date {source_date}",
        )

    # 先清掉目標日舊的計畫
    (
        db.query(TrainingPlanItem)
        .filter(
            TrainingPlanItem.user_id == user_id,
            TrainingPlanItem.date == target_date,
        )
        .delete()
    )

    # 複製 source → target
    for r in source_rows:
        new_row = TrainingPlanItem(
            user_id=user_id,
            date=target_date,
            exercise_name=r.exercise_name,
            target_sets=r.target_sets,
            target_reps=r.target_reps,
            target_weight_kg=r.target_weight_kg,
            note=r.note,
            order_index=r.order_index,
            created_at=datetime.utcnow(),
        )
        db.add(new_row)

    db.commit()

    return _build_day_out(user_id=user_id, target_date=target_date, db=db)


@router.delete("/day")
def delete_day_plan(
    date: date_type = Query(..., description="要刪除的日期（yyyy-mm-dd）"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    刪除某一天的訓練計畫（該日所有項目一起刪）。
    """
    q = db.query(TrainingPlanItem).filter(
        TrainingPlanItem.user_id == user_id,
        TrainingPlanItem.date == date,
    )
    deleted = q.delete()
    db.commit()
    return {"ok": True, "deleted": deleted}

