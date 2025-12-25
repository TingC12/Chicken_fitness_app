# app/routers/store.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user_id
from app.models.economy import StoreItem, InventoryItem, Purchase
from app.schemas.economy import StoreItemRow, PurchaseCreate, PurchaseResult
from app.services.ledger import add_ledger_entry, get_coins_balance

router = APIRouter(prefix="/store", tags=["store"])

@router.get("/items", response_model=list[StoreItemRow])
def list_store_items(db: Session = Depends(get_db)):
    rows = db.query(StoreItem).order_by(StoreItem.id.asc()).all()
    return [
        StoreItemRow(
            id=r.id,
            name=r.name,
            price_coins=r.price_coins,
            exp_min=r.exp_min,
            exp_max=r.exp_max,
            description=r.description,
        )
        for r in rows
    ]

@router.post("/purchase", response_model=PurchaseResult)
def purchase_item(
    payload: PurchaseCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    item = db.query(StoreItem).filter(StoreItem.id == payload.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="item not found")

    coins_before = get_coins_balance(db, user_id)
    if coins_before < item.price_coins:
        raise HTTPException(status_code=400, detail="not enough coins")

    # 1) 建立購買紀錄（紀錄花錢）
    purchase = Purchase(
        user_id=user_id,
        item_id=item.id,
        coins_spent=item.price_coins,
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)

    # 2) 背包 +1（有就加，沒有就新建）
    inv = db.query(InventoryItem).filter(
        InventoryItem.user_id == user_id,
        InventoryItem.item_id == item.id,
    ).first()

    if not inv:
        inv = InventoryItem(user_id=user_id, item_id=item.id, quantity=1)
        db.add(inv)
    else:
        inv.quantity += 1

    db.commit()

    # 3) 金幣總帳扣款
    add_ledger_entry(
        db=db,
        user_id=user_id,
        delta=-item.price_coins,
        source="purchase",
        ref_id=purchase.id,
        idempotency_key=f"purchase:{purchase.id}",
    )

    coins_after = get_coins_balance(db, user_id)

    return PurchaseResult(
        item_id=item.id,
        item_name=item.name,
        coins_spent=item.price_coins,
        coins_after=coins_after,
    )
