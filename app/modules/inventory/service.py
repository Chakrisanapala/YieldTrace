"""
Inventory service for YieldTrace.

CRITICAL DESIGN RULE:
We NEVER let users directly overwrite stock balances.
Balances are calculated from append-only stock movements (stock_moves),
with reconciliation checks and Weighted Average Unit Cost (WAUC) tracking.
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Item,
    StockMove,
    StockMoveDirection,
    StockMoveType,
    AuditLog
)


class InventoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_stock_balance(self, item_id: int) -> float:
        """
        Calculate current physical stock balance strictly by summing append-only ledger entries.
        Balance = SUM(IN) - SUM(OUT)
        """
        in_qty = (
            self.db.query(func.coalesce(func.sum(StockMove.quantity), 0.0))
            .filter(StockMove.item_id == item_id, StockMove.direction == StockMoveDirection.IN)
            .scalar()
        )
        out_qty = (
            self.db.query(func.coalesce(func.sum(StockMove.quantity), 0.0))
            .filter(StockMove.item_id == item_id, StockMove.direction == StockMoveDirection.OUT)
            .scalar()
        )
        return float(in_qty - out_qty)

    def get_all_stock_balances(self) -> List[Dict]:
        """
        Return all items with their ledger-computed stock balances and valuation.
        """
        items = self.db.query(Item).filter(Item.is_active == True).all()
        result = []
        for item in items:
            balance = self.get_stock_balance(item.id)
            result.append({
                "item_id": item.id,
                "code": item.code,
                "name": item.name,
                "category": item.category.value if hasattr(item.category, "value") else str(item.category),
                "unit": item.unit,
                "balance": balance,
                "standard_cost": item.standard_cost,
                "current_wauc": item.current_wauc,
                "inventory_valuation": round(balance * item.current_wauc, 2),
                "reorder_level": item.reorder_level,
                "low_stock_warning": balance < item.reorder_level if item.reorder_level > 0 else False
            })
        return result

    def record_stock_move(
        self,
        item_id: int,
        move_type: StockMoveType,
        direction: StockMoveDirection,
        quantity: float,
        unit: str,
        unit_cost: float,
        reference_type: str,
        reference_id: str,
        notes: Optional[str] = None
    ) -> StockMove:
        """
        Append an immutable stock movement record and compute the running snapshot balance.
        """
        if quantity <= 0:
            raise ValueError(f"Stock movement quantity must be positive, got {quantity}")

        current_balance = self.get_stock_balance(item_id)
        if direction == StockMoveDirection.IN:
            new_balance = current_balance + quantity
        else:
            new_balance = current_balance - quantity

        total_cost = round(quantity * unit_cost, 4)

        move = StockMove(
            item_id=item_id,
            move_type=move_type,
            direction=direction,
            quantity=quantity,
            unit=unit,
            unit_cost=unit_cost,
            total_cost=total_cost,
            reference_type=reference_type,
            reference_id=str(reference_id),
            notes=notes,
            balance_after=new_balance,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(move)
        self.db.flush()
        return move

    def update_weighted_average_cost(self, item_id: int, added_qty: float, purchase_price: float) -> float:
        """
        Update the Weighted Average Unit Cost (WAUC) for an item upon receiving new stock.
        WAUC_new = (Current_Qty * Current_WAUC + Purchase_Qty * Purchase_Price) / (Current_Qty + Purchase_Qty)
        """
        item = self.db.query(Item).filter(Item.id == item_id).first()
        if not item:
            raise ValueError(f"Item with id {item_id} not found")

        current_balance = self.get_stock_balance(item_id)
        old_wauc = item.current_wauc or item.standard_cost or 0.0

        if current_balance <= 0:
            new_wauc = purchase_price
        else:
            total_current_val = current_balance * old_wauc
            total_added_val = added_qty * purchase_price
            new_wauc = (total_current_val + total_added_val) / (current_balance + added_qty)

        item.current_wauc = round(new_wauc, 4)
        self.db.flush()
        return item.current_wauc
