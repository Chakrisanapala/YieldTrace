"""
Sales, Billing, and Receivables API endpoints for YieldTrace.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SalesOrder, Invoice, Customer, Payment, User, UserRole
from app.modules.sales.service import SalesService
from app.modules.auth.service import require_roles

router = APIRouter(prefix="/api/sales", tags=["Sales & Invoicing"])


class OrderLineInput(BaseModel):
    item_id: int
    ordered_quantity: float = Field(gt=0)
    unit_price: float = Field(gt=0)


class CreateOrderRequest(BaseModel):
    order_number: str
    customer_id: int
    lines: List[OrderLineInput]
    notes: Optional[str] = None


class RecordPaymentRequest(BaseModel):
    invoice_id: int
    amount: float = Field(gt=0)
    payment_mode: str = "BANK_TRANSFER"
    reference_no: Optional[str] = None
    notes: Optional[str] = None


@router.post("/orders")
def create_sales_order(
    payload: CreateOrderRequest,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.SALESMAN])),
    db: Session = Depends(get_db)
):
    """Create a new sales order in DRAFT status. Restricted to Owner, Admin, Salesman."""
    service = SalesService(db)
    try:
        lines_data = [l.model_dump() for l in payload.lines]
        order = service.create_sales_order(
            order_number=payload.order_number,
            customer_id=payload.customer_id,
            lines_data=lines_data,
            notes=payload.notes
        )
        return {
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status.value,
            "total_ordered": order.total_ordered_qty
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/approve")
def approve_sales_order(
    order_id: int,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.SALESMAN])),
    db: Session = Depends(get_db)
):
    """Approve an order for fulfillment. Restricted to Owner, Admin, Salesman."""
    service = SalesService(db)
    try:
        order = service.approve_order(order_id)
        return {"id": order.id, "order_number": order.order_number, "status": order.status.value}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/dispatch")
def dispatch_sales_order(
    order_id: int,
    notes: Optional[str] = None,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.PRODUCTION_SUPERVISOR, UserRole.SALESMAN])),
    db: Session = Depends(get_db)
):
    """
    Fulfill and dispatch order based on live inventory.
    Records partial fulfillment, backorders, issues stock moves, and creates GST invoice.
    """
    service = SalesService(db)
    try:
        result = service.dispatch_order(order_id=order_id, notes=notes)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders")
def list_sales_orders(db: Session = Depends(get_db)):
    """List all sales orders with status and fulfillment counts."""
    orders = db.query(SalesOrder).order_by(SalesOrder.id.desc()).all()
    return [
        {
            "id": o.id,
            "order_number": o.order_number,
            "customer_name": o.customer.name if o.customer else None,
            "customer_state": o.customer.state if o.customer else None,
            "status": o.status.value,
            "total_ordered": o.total_ordered_qty,
            "total_fulfilled": o.total_fulfilled_qty,
            "total_backordered": o.total_backordered_qty,
            "order_date": o.order_date.isoformat()
        }
        for o in orders
    ]


@router.get("/invoices")
def list_invoices(db: Session = Depends(get_db)):
    """List all generated GST invoices."""
    invoices = db.query(Invoice).order_by(Invoice.id.desc()).all()
    return [
        {
            "id": inv.id,
            "invoice_no": inv.invoice_no,
            "customer_name": inv.customer.name if inv.customer else None,
            "is_interstate": inv.is_interstate,
            "taxable_amount": inv.taxable_amount,
            "cgst_amount": inv.cgst_amount,
            "sgst_amount": inv.sgst_amount,
            "igst_amount": inv.igst_amount,
            "total_amount": inv.total_amount,
            "paid_amount": inv.paid_amount,
            "outstanding_amount": round(inv.total_amount - inv.paid_amount, 2),
            "status": inv.status.value,
            "invoice_date": inv.invoice_date.isoformat()
        }
        for inv in invoices
    ]


@router.post("/payments")
def record_payment(
    payload: RecordPaymentRequest,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.ACCOUNTANT])),
    db: Session = Depends(get_db)
):
    """Record customer payment against an invoice. Restricted to Owner, Admin, Accountant."""
    service = SalesService(db)
    try:
        pmt = service.record_payment(
            invoice_id=payload.invoice_id,
            amount=payload.amount,
            payment_mode=payload.payment_mode,
            reference_no=payload.reference_no,
            notes=payload.notes
        )
        return {
            "receipt_no": pmt.receipt_no,
            "invoice_id": pmt.invoice_id,
            "amount_paid": pmt.amount,
            "message": "Payment recorded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/customers/{customer_id}/outstanding")
def get_customer_receivables(customer_id: int, db: Session = Depends(get_db)):
    """Get customer's current billing and outstanding balance."""
    service = SalesService(db)
    try:
        return service.get_customer_outstanding(customer_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
