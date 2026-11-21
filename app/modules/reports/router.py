"""
Reports and Export API endpoints for YieldTrace.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.modules.reports.service import ReportsService

router = APIRouter(prefix="/api/reports", tags=["Reports & Audit Exports"])


@router.get("/sales")
def get_sales_register(
    format: str = Query("json"),
    db: Session = Depends(get_db)
):
    """Sales Register Report."""
    service = ReportsService(db)
    data = service.get_sales_register()

    if format == "json":
        return data
    elif format == "csv":
        fieldnames = ["invoice_no", "date", "customer", "state", "is_interstate", "taxable_amount", "cgst", "sgst", "igst", "total_amount", "paid_amount", "outstanding", "status"]
        csv_str = service.export_csv(data, fieldnames)
        return Response(content=csv_str, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=sales_register.csv"})
    elif format == "excel":
        excel_bytes = service.export_excel(data, "Sales Register")
        return Response(content=excel_bytes, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=sales_register.xlsx"})
    elif format == "pdf":
        pdf_bytes = service.export_pdf("Sales Register & GST Summary", data)
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=sales_register.pdf"})


@router.get("/purchases")
def get_purchase_register(
    format: str = Query("json"),
    db: Session = Depends(get_db)
):
    """Purchase Register Report."""
    service = ReportsService(db)
    data = service.get_purchase_register()

    if format == "json":
        return data
    elif format == "csv":
        fieldnames = ["invoice_no", "date", "supplier", "total_amount", "status", "lines_count"]
        csv_str = service.export_csv(data, fieldnames)
        return Response(content=csv_str, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=purchase_register.csv"})
    elif format == "excel":
        excel_bytes = service.export_excel(data, "Purchases")
        return Response(content=excel_bytes, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=purchases.xlsx"})
    elif format == "pdf":
        pdf_bytes = service.export_pdf("Purchase Register", data)
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=purchases.pdf"})


@router.get("/stock-ledger")
def get_stock_ledger_report(
    item_id: Optional[int] = Query(None),
    format: str = Query("json"),
    db: Session = Depends(get_db)
):
    """Append-only Stock Movement Ledger Report."""
    service = ReportsService(db)
    data = service.get_stock_ledger_report(item_id)

    if format == "json":
        return data
    elif format == "csv":
        fieldnames = ["id", "date", "item_code", "item_name", "move_type", "direction", "quantity", "unit", "unit_cost", "reference", "balance_after"]
        csv_str = service.export_csv(data, fieldnames)
        return Response(content=csv_str, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=stock_ledger.csv"})
    elif format == "excel":
        excel_bytes = service.export_excel(data, "Stock Ledger")
        return Response(content=excel_bytes, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=stock_ledger.xlsx"})
    elif format == "pdf":
        pdf_bytes = service.export_pdf("Stock Movement Ledger", data)
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=stock_ledger.pdf"})


@router.get("/production-batches")
def get_production_batch_report(
    format: str = Query("json"),
    db: Session = Depends(get_db)
):
    """Production Batch Performance & Yield Variance Report."""
    service = ReportsService(db)
    data = service.get_production_batch_report()

    if format == "json":
        return data
    elif format == "csv":
        fieldnames = ["run_number", "date", "product", "planned_output", "actual_output", "yield_percent", "yield_variance_percent", "packaging_warning", "supervisor", "is_synthetic"]
        csv_str = service.export_csv(data, fieldnames)
        return Response(content=csv_str, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=production_batches.csv"})
    elif format == "excel":
        excel_bytes = service.export_excel(data, "Production Batches")
        return Response(content=excel_bytes, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=production_batches.xlsx"})
    elif format == "pdf":
        pdf_bytes = service.export_pdf("Production Batch & Yield Report", data)
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=production_batches.pdf"})


@router.get("/customer-receivables")
def get_customer_receivables_report(
    format: str = Query("json"),
    db: Session = Depends(get_db)
):
    """Customer Outstanding Receivables Report."""
    service = ReportsService(db)
    data = service.get_customer_outstanding_report()

    if format == "json":
        return data
    elif format == "csv":
        fieldnames = ["customer_code", "customer_name", "state", "total_invoiced", "total_paid", "outstanding_balance", "invoice_count"]
        csv_str = service.export_csv(data, fieldnames)
        return Response(content=csv_str, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=customer_receivables.csv"})
    elif format == "excel":
        excel_bytes = service.export_excel(data, "Receivables")
        return Response(content=excel_bytes, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=customer_receivables.xlsx"})
    elif format == "pdf":
        pdf_bytes = service.export_pdf("Customer Outstanding Receivables", data)
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=customer_receivables.pdf"})


@router.get("/audit-trail")
def get_audit_trail_report(
    format: str = Query("json"),
    db: Session = Depends(get_db)
):
    """Immutable System Audit Trail Report."""
    service = ReportsService(db)
    data = service.get_audit_trail_report()

    if format == "json":
        return data
    elif format == "csv":
        fieldnames = ["id", "timestamp", "action", "entity", "record_id", "changed_by", "new_values", "reason"]
        csv_str = service.export_csv(data, fieldnames)
        return Response(content=csv_str, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=audit_trail.csv"})
    elif format == "excel":
        excel_bytes = service.export_excel(data, "Audit Trail")
        return Response(content=excel_bytes, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=audit_trail.xlsx"})
    elif format == "pdf":
        pdf_bytes = service.export_pdf("System Audit Trail", data)
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=audit_trail.pdf"})
