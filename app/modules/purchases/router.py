"""
Purchases API endpoints for YieldTrace.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Purchase
from app.modules.purchases.service import PurchaseService

router = APIRouter(prefix="/api/purchases", tags=["Purchases"])


class PurchaseLineInput(BaseModel):
    item_id: int
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    unit: Optional[str] = None


class PurchaseCreateRequest(BaseModel):
    invoice_no: str
    supplier_id: int
    lines: List[PurchaseLineInput]
    notes: Optional[str] = None


@router.post("")
def create_purchase(payload: PurchaseCreateRequest, db: Session = Depends(get_db)):
    """
    Record a purchase receipt, updating item WAUC and writing append-only stock movements.
    """
    service = PurchaseService(db)
    lines_data = [line.model_dump() for line in payload.lines]
    try:
        purchase = service.record_purchase(
            invoice_no=payload.invoice_no,
            supplier_id=payload.supplier_id,
            lines_data=lines_data,
            notes=payload.notes
        )
        return {
            "id": purchase.id,
            "invoice_no": purchase.invoice_no,
            "supplier_id": purchase.supplier_id,
            "total_amount": purchase.total_amount,
            "status": purchase.status,
            "message": "Purchase recorded successfully, stock movements and WAUC updated."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_purchases(db: Session = Depends(get_db)):
    """
    List all recorded purchases.
    """
    purchases = db.query(Purchase).order_by(Purchase.id.desc()).all()
    return [
        {
            "id": p.id,
            "invoice_no": p.invoice_no,
            "supplier": p.supplier.name if p.supplier else None,
            "total_amount": p.total_amount,
            "purchase_date": p.purchase_date.isoformat() if p.purchase_date else None,
            "lines_count": len(p.lines)
        }
        for p in purchases
    ]
