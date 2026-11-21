"""
Purchases service for YieldTrace.
Handles purchase receiving, Weighted Average Unit Cost (WAUC) updates,
Price Variance computation, and append-only inventory ledger writes.
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import (
    Purchase,
    PurchaseLine,
    Item,
    StockMoveType,
    StockMoveDirection,
    AuditLog
)
from app.modules.inventory.service import InventoryService


class PurchaseService:
    def __init__(self, db: Session):
        self.db = db
        self.inventory_service = InventoryService(db)

    def record_purchase(
        self,
        invoice_no: str,
        supplier_id: int,
        lines_data: List[Dict],
        notes: Optional[str] = None
    ) -> Purchase:
        """
        Record a purchase transaction with lines.
        For each line:
        1. Calculate price variance = (actual_unit_price - standard_cost) * quantity
        2. Update Item WAUC
        3. Append to stock_moves (PURCHASE_RECEIPT, direction IN)
        """
        total_amount = sum(line["quantity"] * line["unit_price"] for line in lines_data)

        purchase = Purchase(
            invoice_no=invoice_no,
            supplier_id=supplier_id,
            purchase_date=datetime.now(timezone.utc),
            total_amount=round(total_amount, 2),
            status="RECEIVED",
            notes=notes,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(purchase)
        self.db.flush()

        for line_info in lines_data:
            item_id = line_info["item_id"]
            qty = float(line_info["quantity"])
            unit_price = float(line_info["unit_price"])
            unit = line_info.get("unit")
            line_total = round(qty * unit_price, 2)

            item = self.db.query(Item).filter(Item.id == item_id).first()
            if not item:
                raise ValueError(f"Item {item_id} not found")

            if not unit:
                unit = item.unit

            # Price Variance = (Actual Price - Standard Price) * Actual Quantity
            std_cost = item.standard_cost or unit_price
            price_variance = round((unit_price - std_cost) * qty, 4)

            # Update WAUC before stock move or with current balance
            self.inventory_service.update_weighted_average_cost(item.id, qty, unit_price)

            # Record append-only stock move
            self.inventory_service.record_stock_move(
                item_id=item.id,
                move_type=StockMoveType.PURCHASE_RECEIPT,
                direction=StockMoveDirection.IN,
                quantity=qty,
                unit=unit,
                unit_cost=unit_price,
                reference_type="purchase",
                reference_id=invoice_no,
                notes=f"Invoice {invoice_no} receipt"
            )

            p_line = PurchaseLine(
                purchase_id=purchase.id,
                item_id=item.id,
                quantity=qty,
                unit=unit,
                unit_price=unit_price,
                total_price=line_total,
                price_variance=price_variance
            )
            self.db.add(p_line)

        # Audit log entry
        audit = AuditLog(
            table_name="purchases",
            record_id=invoice_no,
            action="CREATE",
            changed_by="system",
            new_values=f"Invoice {invoice_no}, Total: {total_amount}",
            notes=f"Purchase received from supplier {supplier_id}"
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(purchase)
        return purchase
