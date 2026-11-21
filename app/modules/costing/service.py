"""
Costing and Variance Forensics Engine for YieldTrace.

Calculates:
- Standard BOM cost baseline
- Weighted-average material valuation
- Material Price Variance: impact of purchase price changes
- Material Usage Variance: excess or reduced material consumption
- Yield Variance: impact of producing fewer good packets
- Overhead: direct and allocated run expenses
- Mathematical Cost Waterfall reconciliation without double counting.
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models import ProductionRun, RunConsumption, RunOutput, Overhead, Item


class CostingService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_cost_waterfall(self, run_id: int) -> Dict:
        """
        Reconcile standard BOM cost to actual production cost via variance waterfall.
        Reconciliation equation:
        Actual Cost = Standard Baseline Cost + Price Variance + Usage Variance + Yield Variance + Overheads
        """
        run = self.db.query(ProductionRun).filter(ProductionRun.id == run_id).first()
        if not run:
            raise ValueError(f"ProductionRun {run_id} not found")

        bom = run.bom
        output = run.output
        consumptions = run.consumptions
        overheads = run.overheads

        # 1. Standard BOM Cost baseline
        # Standard cost of planned input materials for this run
        standard_material_cost = sum(c.planned_quantity * c.standard_unit_cost for c in consumptions)

        # 2. Material Usage Variance
        # sum((actual_qty - planned_qty) * standard_unit_cost)
        usage_variance_total = sum(c.usage_variance_cost for c in consumptions)

        # 3. Material Price Variance
        # sum((actual_unit_cost - standard_unit_cost) * actual_qty)
        # Reflects the difference between actual WAUC valuation and standard baseline
        price_variance_total = sum(
            (c.actual_unit_cost - c.standard_unit_cost) * c.actual_quantity
            for c in consumptions
        )

        # 4. Actual Material Cost consumed
        actual_material_cost = sum(c.actual_quantity * c.actual_unit_cost for c in consumptions)

        # 5. Overheads
        total_overheads = sum(oh.amount for oh in overheads) if overheads else 0.0

        # 6. Yield Variance
        # If output produced is lower than planned, the standard material value lost
        standard_cost_per_packet = (
            (standard_material_cost / output.planned_good_packets)
            if output and output.planned_good_packets > 0
            else 0.0
        )
        yield_loss_packets = (
            (output.planned_good_packets - output.actual_good_packets)
            if output
            else 0.0
        )
        yield_variance_total = round(yield_loss_packets * standard_cost_per_packet, 4)

        # 7. Total Actual Production Cost
        total_actual_production_cost = round(
            actual_material_cost + total_overheads, 4
        )

        actual_good_packets = output.actual_good_packets if output else 0.0
        actual_cost_per_packet = (
            round(total_actual_production_cost / actual_good_packets, 4)
            if actual_good_packets > 0
            else 0.0
        )

        # Waterfall steps for visualization and accounting audit
        waterfall_steps = [
            {"label": "Standard Baseline Cost", "amount": round(standard_material_cost, 2), "type": "baseline"},
            {"label": "Price Variance (WAUC vs Std)", "amount": round(price_variance_total, 2), "type": "variance"},
            {"label": "Usage Variance (Excess/Saved Material)", "amount": round(usage_variance_total, 2), "type": "variance"},
            {"label": "Overheads Allocated", "amount": round(total_overheads, 2), "type": "addition"},
            {"label": "Actual Production Cost", "amount": round(total_actual_production_cost, 2), "type": "total"},
        ]

        # Verification check: actual material cost = standard material cost + price var + usage var
        reconciliation_discrepancy = round(
            (standard_material_cost + price_variance_total + usage_variance_total) - actual_material_cost,
            4
        )
        is_reconciled = abs(reconciliation_discrepancy) < 0.01

        return {
            "run_id": run.id,
            "run_number": run.run_number,
            "standard_material_cost": round(standard_material_cost, 2),
            "price_variance": round(price_variance_total, 2),
            "usage_variance": round(usage_variance_total, 2),
            "yield_variance": round(yield_variance_total, 2),
            "yield_loss_packets": yield_loss_packets,
            "total_overheads": round(total_overheads, 2),
            "actual_material_cost": round(actual_material_cost, 2),
            "total_actual_production_cost": round(total_actual_production_cost, 2),
            "standard_cost_per_packet": round(standard_cost_per_packet, 4),
            "actual_cost_per_packet": actual_cost_per_packet,
            "is_mathematically_reconciled": is_reconciled,
            "reconciliation_discrepancy": reconciliation_discrepancy,
            "waterfall_steps": waterfall_steps
        }
