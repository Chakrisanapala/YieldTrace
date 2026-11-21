"""
Enterprise Reports and Export Generation Service for YieldTrace.

Supports:
- 14 Operational, Variance Forensics & Compliance Reports
- Formats: CSV, Excel (OpenPyXL), PDF (ReportLab)
- Immutable Audit Trail logs
"""
import io
import csv
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.models import (
    Invoice,
    Purchase,
    StockMove,
    ProductionRun,
    RunConsumption,
    RunOutput,
    Customer,
    Item,
    ItemCategory,
    AuditLog,
    VarianceFinding
)
from app.modules.inventory.service import InventoryService


class ReportsService:
    def __init__(self, db: Session):
        self.db = db
        self.inventory_service = InventoryService(db)

    def get_sales_register(self) -> List[Dict]:
        """Report 1: Sales Register with GST breakdown."""
        invoices = self.db.query(Invoice).order_by(Invoice.invoice_date.desc()).all()
        return [
            {
                "invoice_no": inv.invoice_no,
                "date": inv.invoice_date.strftime("%Y-%m-%d"),
                "customer": inv.customer.name if inv.customer else "",
                "state": inv.customer.state if inv.customer else "",
                "is_interstate": "Yes" if inv.is_interstate else "No",
                "taxable_amount": inv.taxable_amount,
                "cgst": inv.cgst_amount,
                "sgst": inv.sgst_amount,
                "igst": inv.igst_amount,
                "total_amount": inv.total_amount,
                "paid_amount": inv.paid_amount,
                "outstanding": round(inv.total_amount - inv.paid_amount, 2),
                "status": inv.status.value
            }
            for inv in invoices
        ]

    def get_purchase_register(self) -> List[Dict]:
        """Report 2: Purchase Register."""
        purchases = self.db.query(Purchase).order_by(Purchase.purchase_date.desc()).all()
        return [
            {
                "invoice_no": p.invoice_no,
                "date": p.purchase_date.strftime("%Y-%m-%d"),
                "supplier": p.supplier.name if p.supplier else "",
                "total_amount": p.total_amount,
                "status": p.status,
                "lines_count": len(p.lines)
            }
            for p in purchases
        ]

    def get_stock_ledger_report(self, item_id: Optional[int] = None) -> List[Dict]:
        """Report 6: Immutable Stock Movement Ledger Report."""
        query = self.db.query(StockMove)
        if item_id:
            query = query.filter(StockMove.item_id == item_id)
        moves = query.order_by(StockMove.id.desc()).limit(200).all()

        return [
            {
                "id": m.id,
                "date": m.created_at.strftime("%Y-%m-%d %H:%M"),
                "item_code": m.item.code if m.item else "",
                "item_name": m.item.name if m.item else "",
                "move_type": m.move_type.value,
                "direction": m.direction.value,
                "quantity": m.quantity,
                "unit": m.unit,
                "unit_cost": m.unit_cost,
                "reference": f"{m.reference_type} #{m.reference_id}",
                "balance_after": m.balance_after
            }
            for m in moves
        ]

    def get_production_batch_report(self) -> List[Dict]:
        """Report 7: Production Batch Performance & Yield. Production batches appear before synthetic demo history."""
        runs = self.db.query(ProductionRun).order_by(ProductionRun.is_synthetic.asc(), ProductionRun.id.desc()).all()
        result = []
        for r in runs:
            ro = r.output
            result.append({
                "run_number": r.run_number,
                "date": r.start_time.strftime("%Y-%m-%d"),
                "product": ro.finished_good.name if ro and ro.finished_good else "",
                "planned_output": ro.planned_good_packets if ro else 0,
                "actual_output": ro.actual_good_packets if ro else 0,
                "yield_percent": ro.yield_percentage if ro else 0.0,
                "yield_variance_percent": ro.yield_variance_percentage if ro else 0.0,
                "packaging_warning": "YES - MISMATCH" if ro and ro.packaging_mismatch else "OK",
                "supervisor": r.supervisor,
                "is_synthetic": "Synthetic Demo" if r.is_synthetic else "Production"
            })
        return result

    def get_customer_outstanding_report(self) -> List[Dict]:
        """Report 11: Customer Outstanding Receivables."""
        customers = self.db.query(Customer).all()
        result = []
        for c in customers:
            total_inv = sum(inv.total_amount for inv in c.invoices)
            total_paid = sum(inv.paid_amount for inv in c.invoices)
            bal = round(total_inv - total_paid, 2)
            result.append({
                "customer_code": c.code,
                "customer_name": c.name,
                "state": c.state,
                "total_invoiced": round(total_inv, 2),
                "total_paid": round(total_paid, 2),
                "outstanding_balance": bal,
                "invoice_count": len(c.invoices)
            })
        return result

    def get_audit_trail_report(self) -> List[Dict]:
        """Report 12: Immutable System Audit Logs."""
        logs = self.db.query(AuditLog).order_by(AuditLog.id.desc()).limit(150).all()
        return [
            {
                "id": l.id,
                "timestamp": l.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "action": l.action,
                "entity": l.table_name,
                "record_id": l.record_id,
                "changed_by": l.changed_by,
                "new_values": l.new_values,
                "reason": l.reason or ""
            }
            for l in logs
        ]

    # Export Helpers: CSV, Excel, PDF
    def export_csv(self, data: List[Dict], fieldnames: List[str]) -> str:
        """Export tabular records to CSV formatted string."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
        return output.getvalue()

    def export_excel(self, data: List[Dict], sheet_title: str = "Report") -> bytes:
        """Export tabular records to OpenPyXL Excel spreadsheet."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_title

        if not data:
            ws.append(["No records found"])
            buf = io.BytesIO()
            wb.save(buf)
            return buf.getvalue()

        headers = list(data[0].keys())
        ws.append([h.replace("_", " ").title() for h in headers])

        # Style Header
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Append Data
        for row in data:
            ws.append([row.get(h, "") for h in headers])

        # Adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def export_pdf(self, title: str, data: List[Dict]) -> bytes:
        """Generate PDF report using ReportLab."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            leftMargin=30,
            rightMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name="TitleStyle",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.HexColor("#1E3A8A"),
            spaceAfter=15
        )

        elements.append(Paragraph(f"YieldTrace — {title}", title_style))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}", styles["Normal"]))
        elements.append(Spacer(1, 15))

        if not data:
            elements.append(Paragraph("No records found.", styles["Normal"]))
        else:
            headers = [k.replace("_", " ").title() for k in data[0].keys()]
            table_data = [headers]
            for row in data:
                table_data.append([str(row.get(k, "")) for k in data[0].keys()])

            table = Table(table_data)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")])
            ]))
            elements.append(table)

        doc.build(elements)
        return buffer.getvalue()
