# app/services/ledger.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.models.economy import CoinsLedger

def get_coins_balance(db: Session, user_id: int) -> int:
    total = db.query(func.coalesce(func.sum(CoinsLedger.delta), 0)).filter(
        CoinsLedger.user_id == user_id
    ).scalar()
    return int(total or 0)

def add_ledger_entry(
    db: Session,
    user_id: int,
    delta: int,
    source: str,
    ref_id: int | None,
    idempotency_key: str | None,
) -> int:
    """
    Idempotent ledger insert.
    - 若已存在同一筆（用 idempotency_key 優先，其次 source+ref_id），回傳既有 delta（不要回 0）
    - 若不存在才插入，並回傳本次 delta
    """
    exists = None

    # ✅ 1) 優先用 idempotency_key 做冪等（最穩）
    if idempotency_key:
        exists = db.query(CoinsLedger).filter(
            CoinsLedger.user_id == user_id,
            CoinsLedger.idempotency_key == idempotency_key,
        ).first()

    # ✅ 2) 沒有 idempotency_key 再用 source + ref_id
    if not exists and ref_id is not None:
        exists = db.query(CoinsLedger).filter(
            CoinsLedger.user_id == user_id,
            CoinsLedger.source == source,
            CoinsLedger.ref_id == ref_id,
        ).first()

    # ✅ 已存在：回傳既有 delta（避免重試把 coins_awarded 洗成 0）
    if exists:
        return int(exists.delta)

    row = CoinsLedger(
        user_id=user_id,
        delta=delta,
        source=source,
        ref_id=ref_id,
        idempotency_key=idempotency_key,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    return int(delta)
