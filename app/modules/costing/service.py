"""
Costing and Mathematical Cost Waterfall Reconciliation Engine for YieldTrace.

Calculates:
- Standard BOM cost baseline for planned output
- Actual material cost evaluated via Weighted Average Unit Cost (WAUC)
- Material Price Variance: (Actual WAUC - Standard Cost) * Actual Quantity
- Material Usage Variance: (Actual Qty - Planned Qty) * Standard Cost
- Overhead Variance: Actual Overhead - Standard Overhead
- Standard Yield-Loss Effect: (Planned Packets - Actual Packets) * Standard Unit Cost
- Reconciled Cost Waterfall asserting EXACT mathematical balance down to the paisa (0.00 discrepancy).
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models import ProductionRun, RunConsumption, RunOutput, Overhead, Item, BOM


def to_decimal(val: float | int | str | Decimal) -> Decimal:
    return Decimal(str(val))


def quantize_currency(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class CostingService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_cost_waterfall(self, run_id: int) -> Dict:
        """
        Reconcile standard BOM cost to actual production cost via variance waterfall.
        Reconciliation equation:
        Actual Batch Cost = Standard Baseline Cost + Material Price Variance + Material Usage Variance + Overhead Variance
        """
        run = self.db.query(ProductionRun).filter(ProductionRun.id == run_id).first()
        if not run:
            raise ValueError(f"ProductionRun #{run_id} not found")

        bom = run.bom
        output = run.output
        consumptions = run.consumptions
        overheads = run.overheads

        # 1. Standard Planned Material Cost
        # Sum of (planned_qty * standard_unit_cost)
        standard_mat_cost_d = Decimal("0.00")
        actual_mat_cost_d = Decimal("0.00")
        usage_var_total_d = Decimal("0.00")
        price_var_total_d = Decimal("0.00")

        material_breakdown = []

        for c in consumptions:
            p_qty = to_decimal(c.planned_quantity)
            a_qty = to_decimal(c.actual_quantity)
            s_cost = to_decimal(c.standard_unit_cost)
            a_cost = to_decimal(c.actual_unit_cost)

            std_cost_line = p_qty * s_cost
            act_cost_line = a_qty * a_cost

            # Usage Variance = (Actual Qty - Planned Qty) * Standard Cost
            u_var = (a_qty - p_qty) * s_cost
            # Price Variance = (Actual Cost - Standard Cost) * Actual Qty
            p_var = (a_cost - s_cost) * a_qty

            standard_mat_cost_d += std_cost_line
            actual_mat_cost_d += act_cost_line
            usage_var_total_d += u_var
            price_var_total_d += p_var

            material_breakdown.append({
                "item_id": c.item_id,
                "item_code": c.item.code if c.item else None,
                "item_name": c.item.name if c.item else None,
                "planned_quantity": float(p_qty),
                "actual_quantity": float(a_qty),
                "unit": c.unit,
                "standard_cost": float(s_cost),
                "actual_wauc": float(a_cost),
                "standard_total": float(quantize_currency(std_cost_line)),
                "actual_total": float(quantize_currency(act_cost_line)),
                "usage_variance": float(quantize_currency(u_var)),
                "price_variance": float(quantize_currency(p_var))
            })

        # 2. Overheads
        standard_overhead_d = to_decimal(bom.standard_overhead if bom else 1800.0) * to_decimal(run.planned_batches)
        actual_overhead_d = sum(to_decimal(oh.amount) for oh in overheads) if overheads else Decimal("0.00")
        overhead_variance_d = actual_overhead_d - standard_overhead_d

        # 3. Total Standard Batch Baseline & Total Actual Cost
        total_standard_cost_d = standard_mat_cost_d + standard_overhead_d
        total_actual_cost_d = actual_mat_cost_d + actual_overhead_d

        # 4. Yield Analysis
        planned_packets = to_decimal(output.planned_good_packets if output else 200.0)
        actual_packets = to_decimal(output.actual_good_packets if output else 0.0)
        yield_loss_packets_d = planned_packets - actual_packets

        standard_cost_per_packet_d = (
            total_standard_cost_d / planned_packets
            if planned_packets > Decimal("0.00")
            else Decimal("0.00")
        )
        actual_cost_per_packet_d = (
            total_actual_cost_d / actual_packets
            if actual_packets > Decimal("0.00")
            else Decimal("0.00")
        )

        # Standard yield-loss effect (cost of lost packets at standard unit cost)
        standard_yield_loss_effect_d = yield_loss_packets_d * standard_cost_per_packet_d

        # Mathematical bridge check:
        # Bridge: Standard Cost + Price Variance + Usage Variance + Overhead Variance
        reconciled_sum_d = total_standard_cost_d + price_var_total_d + usage_var_total_d + overhead_variance_d
        discrepancy_d = quantize_currency(reconciled_sum_d - total_actual_cost_d)
        is_reconciled = (discrepancy_d == Decimal("0.00"))

        # Visual waterfall steps for frontend Chart.js rendering
        waterfall_steps = [
            {"label": "Standard BOM Baseline", "amount": float(quantize_currency(total_standard_cost_d)), "type": "baseline"},
            {"label": "Material Price Variance", "amount": float(quantize_currency(price_var_total_d)), "type": "variance"},
            {"label": "Material Usage Variance", "amount": float(quantize_currency(usage_var_total_d)), "type": "variance"},
            {"label": "Overhead Variance", "amount": float(quantize_currency(overhead_variance_d)), "type": "variance"},
            {"label": "Actual Batch Cost", "amount": float(quantize_currency(total_actual_cost_d)), "type": "total"}
        ]

        return {
            "run_id": run.id,
            "run_number": run.run_number,
            "standard_material_cost": float(quantize_currency(standard_mat_cost_d)),
            "actual_material_cost": float(quantize_currency(actual_mat_cost_d)),
            "price_variance": float(quantize_currency(price_var_total_d)),
            "usage_variance": float(quantize_currency(usage_var_total_d)),
            "standard_overhead": float(quantize_currency(standard_overhead_d)),
            "actual_overhead": float(quantize_currency(actual_overhead_d)),
            "overhead_variance": float(quantize_currency(overhead_variance_d)),
            "total_standard_cost": float(quantize_currency(total_standard_cost_d)),
            "total_actual_cost": float(quantize_currency(total_actual_cost_d)),
            "planned_packets": float(planned_packets),
            "actual_good_packets": float(actual_packets),
            "yield_loss_packets": float(yield_loss_packets_d),
            "standard_cost_per_packet": float(standard_cost_per_packet_d.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
            "actual_cost_per_packet": float(actual_cost_per_packet_d.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
            "standard_yield_loss_effect": float(quantize_currency(standard_yield_loss_effect_d)),
            "is_mathematically_reconciled": is_reconciled,
            "reconciliation_discrepancy": float(discrepancy_d),
            "material_breakdown": material_breakdown,
            "waterfall_steps": waterfall_steps
        }
