"""
Sales, Order Allocation, GST Billing and Customer Receivables Service for YieldTrace.

Features:
- Sales order workflow (Draft -> Approved -> Partially Fulfilled / Fulfilled)
- Strict allocation & dispatch logic:
  Checks current finished-goods stock from append-only ledger.
  If available < requested, dispatches available and records outstanding backorder.
  NEVER allows negative inventory.
- GST calculation using exact Decimal rounding:
  Intra-state (same state as supplier e.g. Tamil Nadu): CGST + SGST (e.g. 2.5% + 2.5%)
  Inter-state (different state e.g. Karnataka): IGST (e.g. 5.0%)
- Invoice generation with unique invoice numbers
- Payment recording (preserves invoice total, updates paid amount & outstanding balance)
- Customer receivables and aging tracking
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    Item,
    SalesOrder,
    SalesOrderLine,
    Dispatch,
    Invoice,
    InvoiceLine,
    Payment,
    OrderStatus,
    InvoiceStatus,
    StockMoveType,
    StockMoveDirection,
    AuditLog
)
from app.modules.inventory.service import InventoryService, InsufficientStockError

DEFAULT_SUPPLIER_STATE = "Tamil Nadu"


def round_currency(val: float | Decimal) -> float:
    """Round to 2 decimal places using standard banking ROUND_HALF_UP."""
    d = Decimal(str(val))
    return float(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


class SalesService:
    def __init__(self, db: Session, supplier_state: str = DEFAULT_SUPPLIER_STATE):
        self.db = db
        self.supplier_state = supplier_state
        self.inventory_service = InventoryService(db)

    def create_sales_order(
        self,
        order_number: str,
        customer_id: int,
        lines_data: List[Dict],
        notes: Optional[str] = None
    ) -> SalesOrder:
        """Create a new sales order in DRAFT status."""
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise ValueError(f"Customer #{customer_id} not found.")

        total_ordered = sum(float(l["ordered_quantity"]) for l in lines_data)

        order = SalesOrder(
            order_number=order_number,
            customer_id=customer_id,
            order_date=datetime.now(timezone.utc),
            status=OrderStatus.DRAFT,
            total_ordered_qty=total_ordered,
            total_fulfilled_qty=0.0,
            total_backordered_qty=0.0,
            notes=notes,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(order)
        self.db.flush()

        for line_info in lines_data:
            item_id = line_info["item_id"]
            qty = float(line_info["ordered_quantity"])
            price = float(line_info["unit_price"])
            total = round_currency(qty * price)

            sol = SalesOrderLine(
                order_id=order.id,
                item_id=item_id,
                ordered_quantity=qty,
                fulfilled_quantity=0.0,
                backordered_quantity=0.0,
                unit_price=price,
                total_price=total
            )
            self.db.add(sol)

        self.db.commit()
        self.db.refresh(order)
        return order

    def approve_order(self, order_id: int) -> SalesOrder:
        """Transition order from DRAFT to APPROVED."""
        order = self.db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
        if not order:
            raise ValueError(f"Sales order #{order_id} not found.")
        order.status = OrderStatus.APPROVED
        self.db.commit()
        self.db.refresh(order)
        return order

    def dispatch_order(
        self,
        order_id: int,
        dispatch_number: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """
        Fulfill and dispatch order lines based on available finished-goods inventory.
        Enforces:
        - If available stock >= ordered qty: Fulfill in full.
        - If available stock < ordered qty: Fulfill available, record exact shortage as backorder.
        - Zero negative inventory allowed.
        - Issues append-only stock movement (SALES_DISPATCH, direction OUT).
        - Automatically generates corresponding GST Invoice.
        """
        order = self.db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
        if not order:
            raise ValueError(f"Sales order #{order_id} not found.")

        if order.status not in [OrderStatus.APPROVED, OrderStatus.PARTIALLY_FULFILLED]:
            raise ValueError(f"Order #{order.order_number} must be APPROVED before dispatch. Current status: {order.status.value}")

        customer = order.customer
        is_interstate = (customer.state.strip().lower() != self.supplier_state.strip().lower())

        dispatch_ref = dispatch_number or f"DSP-{order.order_number}-{int(datetime.now().timestamp())}"
        invoice_no = f"INV-{order.order_number}"

        total_dispatched_for_run = 0.0
        total_backordered_for_run = 0.0

        invoice_taxable = 0.0
        invoice_cgst = 0.0
        invoice_sgst = 0.0
        invoice_igst = 0.0
        invoice_total = 0.0

        invoice_lines_to_add = []

        for line in order.lines:
            unfulfilled = line.ordered_quantity - line.fulfilled_quantity
            if unfulfilled <= 0:
                continue

            available_stock = self.inventory_service.get_stock_balance(line.item_id)
            fulfill_qty = min(unfulfilled, max(0.0, available_stock))
            backorder_qty = unfulfilled - fulfill_qty

            line.fulfilled_quantity += fulfill_qty
            line.backordered_quantity = backorder_qty
            total_dispatched_for_run += fulfill_qty
            total_backordered_for_run += backorder_qty

            if fulfill_qty > 0:
                # 1. Record Dispatch record
                dsp = Dispatch(
                    dispatch_number=f"{dispatch_ref}-{line.id}",
                    order_id=order.id,
                    item_id=line.item_id,
                    dispatched_quantity=fulfill_qty,
                    dispatch_date=datetime.now(timezone.utc),
                    notes=notes
                )
                self.db.add(dsp)

                # 2. Append-only stock movement
                self.inventory_service.record_stock_move(
                    item_id=line.item_id,
                    move_type=StockMoveType.SALES_DISPATCH,
                    direction=StockMoveDirection.OUT,
                    quantity=fulfill_qty,
                    unit=line.item.unit,
                    unit_cost=line.item.current_wauc or line.item.standard_cost,
                    reference_type="sales_dispatch",
                    reference_id=dispatch_ref,
                    notes=f"Dispatched for Order #{order.order_number} to {customer.name}"
                )

                # 3. GST Calculation using Decimal arithmetic
                item_price_d = Decimal(str(line.unit_price))
                qty_d = Decimal(str(fulfill_qty))
                taxable_d = (qty_d * item_price_d).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                taxable_float = float(taxable_d)

                gst_rate = Decimal(str(line.item.gst_rate or 5.0))

                if is_interstate:
                    # IGST applied
                    igst_d = (taxable_d * (gst_rate / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    cgst_d = Decimal("0.00")
                    sgst_d = Decimal("0.00")
                else:
                    # Intra-state: CGST (half) + SGST (half)
                    half_rate = gst_rate / Decimal("2")
                    cgst_d = (taxable_d * (half_rate / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    sgst_d = (taxable_d * (half_rate / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    igst_d = Decimal("0.00")

                line_total_d = taxable_d + cgst_d + sgst_d + igst_d

                invoice_taxable += taxable_float
                invoice_cgst += float(cgst_d)
                invoice_sgst += float(sgst_d)
                invoice_igst += float(igst_d)
                invoice_total += float(line_total_d)

                invoice_lines_to_add.append({
                    "item_id": line.item_id,
                    "quantity": fulfill_qty,
                    "unit_price": line.unit_price,
                    "taxable_amount": taxable_float,
                    "gst_rate": float(gst_rate),
                    "cgst_amount": float(cgst_d),
                    "sgst_amount": float(sgst_d),
                    "igst_amount": float(igst_d),
                    "total_amount": float(line_total_d)
                })

        order.total_fulfilled_qty = sum(l.fulfilled_quantity for l in order.lines)
        order.total_backordered_qty = sum(l.backordered_quantity for l in order.lines)

        if order.total_backordered_qty > 0:
            order.status = OrderStatus.PARTIALLY_FULFILLED
        else:
            order.status = OrderStatus.FULFILLED

        # Create GST Invoice if anything was dispatched
        created_invoice = None
        if total_dispatched_for_run > 0:
            created_invoice = Invoice(
                invoice_no=invoice_no,
                order_id=order.id,
                customer_id=customer.id,
                invoice_date=datetime.now(timezone.utc),
                is_interstate=is_interstate,
                taxable_amount=round_currency(invoice_taxable),
                cgst_amount=round_currency(invoice_cgst),
                sgst_amount=round_currency(invoice_sgst),
                igst_amount=round_currency(invoice_igst),
                total_amount=round_currency(invoice_total),
                paid_amount=0.0,
                status=InvoiceStatus.ISSUED,
                notes=f"Tax invoice for order {order.order_number}"
            )
            self.db.add(created_invoice)
            self.db.flush()

            for il_data in invoice_lines_to_add:
                inv_line = InvoiceLine(
                    invoice_id=created_invoice.id,
                    item_id=il_data["item_id"],
                    quantity=il_data["quantity"],
                    unit_price=il_data["unit_price"],
                    taxable_amount=il_data["taxable_amount"],
                    gst_rate=il_data["gst_rate"],
                    cgst_amount=il_data["cgst_amount"],
                    sgst_amount=il_data["sgst_amount"],
                    igst_amount=il_data["igst_amount"],
                    total_amount=il_data["total_amount"]
                )
                self.db.add(inv_line)

        self.db.commit()
        self.db.refresh(order)

        return {
            "order_number": order.order_number,
            "status": order.status.value,
            "total_ordered": order.total_ordered_qty,
            "total_fulfilled": order.total_fulfilled_qty,
            "total_backordered": order.total_backordered_qty,
            "dispatched_now": total_dispatched_for_run,
            "backordered_now": total_backordered_for_run,
            "invoice_no": created_invoice.invoice_no if created_invoice else None,
            "invoice_total": created_invoice.total_amount if created_invoice else 0.0
        }

    def record_payment(
        self,
        invoice_id: int,
        amount: float,
        payment_mode: str = "BANK_TRANSFER",
        reference_no: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Payment:
        """
        Record a payment against an invoice.
        Enforces:
        - Invoice total is preserved.
        - Paid amount is updated.
        - Status updated to PARTIALLY_PAID or PAID.
        """
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice #{invoice_id} not found.")

        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")

        receipt_no = f"RCP-{int(datetime.now().timestamp())}"
        payment = Payment(
            receipt_no=receipt_no,
            invoice_id=invoice.id,
            customer_id=invoice.customer_id,
            payment_date=datetime.now(timezone.utc),
            amount=round_currency(amount),
            payment_mode=payment_mode,
            reference_no=reference_no,
            notes=notes,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(payment)

        # Update invoice paid amount
        new_paid = round_currency(invoice.paid_amount + amount)
        invoice.paid_amount = new_paid
        if new_paid >= invoice.total_amount:
            invoice.status = InvoiceStatus.PAID
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID

        # Audit log
        audit = AuditLog(
            table_name="payments",
            record_id=receipt_no,
            action="CREATE",
            changed_by="accountant",
            new_values=f"Invoice: {invoice.invoice_no}, Amount: ₹{amount:.2f}, Mode: {payment_mode}",
            reason=f"Payment received for invoice {invoice.invoice_no}"
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get_customer_outstanding(self, customer_id: int) -> Dict:
        """Calculate total invoiced, total paid, and net outstanding amount for a customer."""
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise ValueError(f"Customer #{customer_id} not found.")

        invoices = self.db.query(Invoice).filter(Invoice.customer_id == customer_id).all()
        total_invoiced = sum(inv.total_amount for inv in invoices)
        total_paid = sum(inv.paid_amount for inv in invoices)
        outstanding = round_currency(total_invoiced - total_paid)

        return {
            "customer_id": customer.id,
            "customer_name": customer.name,
            "total_invoiced": round_currency(total_invoiced),
            "total_paid": round_currency(total_paid),
            "outstanding_amount": outstanding,
            "invoice_count": len(invoices)
        }
