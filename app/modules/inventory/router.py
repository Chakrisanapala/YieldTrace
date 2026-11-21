"""
Inventory API endpoints for YieldTrace.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Item, StockMove
from app.modules.inventory.service import InventoryService

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


@router.get("/balances")
def get_inventory_balances(db: Session = Depends(get_db)):
    """
    Returns current stock balances for all active items.
    Strictly calculated from the append-only stock_moves ledger.
    """
    service = InventoryService(db)
    return service.get_all_stock_balances()


@router.get("/item/{item_id}")
def get_item_detail(item_id: int, db: Session = Depends(get_db)):
    """
    Returns details of a specific item, its current balance, and recent ledger moves.
    """
    service = InventoryService(db)
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    balance = service.get_stock_balance(item.id)
    recent_moves = (
        db.query(StockMove)
        .filter(StockMove.item_id == item.id)
        .order_by(StockMove.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "item": {
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "category": item.category.value,
            "unit": item.unit,
            "standard_cost": item.standard_cost,
            "current_wauc": item.current_wauc,
            "balance": balance,
            "valuation": round(balance * item.current_wauc, 2)
        },
        "moves": [
            {
                "id": m.id,
                "move_type": m.move_type.value,
                "direction": m.direction.value,
                "quantity": m.quantity,
                "unit": m.unit,
                "unit_cost": m.unit_cost,
                "reference_type": m.reference_type,
                "reference_id": m.reference_id,
                "balance_after": m.balance_after,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in recent_moves
        ]
    }


@router.get("/ledger")
def get_stock_ledger(
    item_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    View the append-only stock movement ledger.
    """
    query = db.query(StockMove)
    if item_id:
        query = query.filter(StockMove.item_id == item_id)
    moves = query.order_by(StockMove.id.desc()).limit(limit).all()

    return [
        {
            "id": m.id,
            "item_id": m.item_id,
            "item_code": m.item.code if m.item else None,
            "item_name": m.item.name if m.item else None,
            "move_type": m.move_type.value,
            "direction": m.direction.value,
            "quantity": m.quantity,
            "unit": m.unit,
            "unit_cost": m.unit_cost,
            "total_cost": m.total_cost,
            "reference_type": m.reference_type,
            "reference_id": m.reference_id,
            "balance_after": m.balance_after,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in moves
    ]
