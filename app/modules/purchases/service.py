"""
Purchases Service for YieldTrace.

Features:
- Idempotency control: Prevents duplicate supplier receipts using transaction references
- Price Variance calculation: (Actual unit price - Standard cost) * Actual quantity
- Dynamic Weighted Average Unit Cost (WAUC) update
- Append-only stock movements (PURCHASE_RECEIPT, direction IN)
- Audit log tracking
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


class DuplicatePurchaseError(Exception):
    """Raised when an invoice or idempotency token has already been recorded."""
    pass


class PurchaseService:
    def __init__(self, db: Session):
        self.db = db
        self.inventory_service = InventoryService(db)

    def record_purchase(
        self,
        invoice_no: str,
        supplier_id: int,
        lines_data: List[Dict],
        idempotency_token: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Purchase:
        """
        Record a purchase transaction with lines.
        Guards:
        - Prevents duplicate invoice numbers
        - Checks idempotency token
        - Updates WAUC
        - Writes append-only stock movement
        """
        # 1. Idempotency & duplicate check
        existing_invoice = self.db.query(Purchase).filter(Purchase.invoice_no == invoice_no).first()
        if existing_invoice:
            raise DuplicatePurchaseError(f"Purchase invoice '{invoice_no}' has already been recorded.")

        if idempotency_token:
            existing_token = self.db.query(Purchase).filter(Purchase.idempotency_token == idempotency_token).first()
            if existing_token:
                raise DuplicatePurchaseError(f"Transaction with idempotency token '{idempotency_token}' already processed.")

        total_amount = sum(float(line["quantity"]) * float(line["unit_price"]) for line in lines_data)

        purchase = Purchase(
            invoice_no=invoice_no,
            supplier_id=supplier_id,
            purchase_date=datetime.now(timezone.utc),
            total_amount=round(total_amount, 2),
            status="RECEIVED",
            idempotency_token=idempotency_token,
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
                raise ValueError(f"Item with ID {item_id} not found")

            if not unit:
                unit = item.unit

            # Price Variance = (Actual Price - Standard Price) * Actual Quantity
            std_cost = item.standard_cost or unit_price
            price_variance = round((unit_price - std_cost) * qty, 4)

            # Update WAUC with incoming quantity
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
                notes=f"Purchase invoice {invoice_no} receipt"
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
            changed_by="procurement",
            new_values=f"Invoice: {invoice_no}, Amount: ₹{total_amount:.2f}",
            reason=f"Purchase goods receipt from supplier #{supplier_id}"
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(purchase)
        return purchase
