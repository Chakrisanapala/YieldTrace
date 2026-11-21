"""
Main Dashboard & Executive Analytics API for YieldTrace.

Calculates real-time KPIs strictly from database records:
- Total Sales & Invoicing
- Order counts & Pending orders
- Production Batches & Average Yield
- Live Finished Goods & Raw Material Balances
- Customer Receivables / Outstanding
- Active Forensic Warnings & Packaging Mismatches
- Recent activity audit feed
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import (
    Invoice,
    SalesOrder,
    OrderStatus,
    ProductionRun,
    RunOutput,
    Item,
    ItemCategory,
    AuditLog,
    VarianceFinding
)
from app.modules.inventory.service import InventoryService

router = APIRouter(prefix="/api/dashboard", tags=["Executive Dashboard"])


@router.get("/metrics")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Return live enterprise KPIs calculated strictly from operational records."""
    inv_service = InventoryService(db)

    # 1. Sales & Invoicing
    invoices = db.query(Invoice).all()
    total_sales = sum(inv.total_amount for inv in invoices)
    total_paid = sum(inv.paid_amount for inv in invoices)
    total_outstanding = round(total_sales - total_paid, 2)

    # 2. Orders
    orders = db.query(SalesOrder).all()
    total_orders = len(orders)
    pending_orders = sum(1 for o in orders if o.status in [OrderStatus.DRAFT, OrderStatus.APPROVED, OrderStatus.PARTIALLY_FULFILLED])

    # 3. Production & Yield
    runs = db.query(ProductionRun).all()
    total_runs = len(runs)
    outputs = [r.output for r in runs if r.output]
    avg_yield = (
        round(sum(o.yield_percentage for o in outputs) / len(outputs), 1)
        if outputs else 0.0
    )
    packaging_warnings_count = sum(1 for o in outputs if o.packaging_mismatch)

    # 4. Inventory Balances
    items = db.query(Item).filter(Item.is_active == True).all()
    total_rm_valuation = 0.0
    total_fg_packets = 0.0
    total_fg_valuation = 0.0

    for item in items:
        bal = inv_service.get_stock_balance(item.id)
        val = bal * (item.current_wauc or item.standard_cost)
        if item.category == ItemCategory.FINISHED_GOOD:
            total_fg_packets += bal
            total_fg_valuation += val
        elif item.category == ItemCategory.RAW_MATERIAL:
            total_rm_valuation += val

    # 5. Forensic Anomalies
    total_findings = db.query(VarianceFinding).count()
    critical_findings = db.query(VarianceFinding).filter(VarianceFinding.severity == "CRITICAL").count()

    # 6. Recent Operational Activity
    recent_logs = (
        db.query(AuditLog)
        .order_by(AuditLog.id.desc())
        .limit(8)
        .all()
    )
    activity_feed = [
        {
            "id": l.id,
            "action": l.action,
            "entity": l.table_name,
            "reference": l.record_id,
            "changed_by": l.changed_by,
            "reason": l.reason or l.new_values or "",
            "timestamp": l.created_at.strftime("%H:%M:%S, %d %b %Y")
        }
        for l in recent_logs
    ]

    return {
        "kpis": {
            "total_sales": round(total_sales, 2),
            "total_outstanding": total_outstanding,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "production_batches": total_runs,
            "average_yield_percent": avg_yield,
            "packaging_warnings": packaging_warnings_count,
            "finished_goods_inventory_units": int(total_fg_packets),
            "finished_goods_valuation": round(total_fg_valuation, 2),
            "raw_materials_valuation": round(total_rm_valuation, 2),
            "total_anomalies_flagged": total_findings,
            "critical_anomalies": critical_findings
        },
        "recent_activity": activity_feed
    }
