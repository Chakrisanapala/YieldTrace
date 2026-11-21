"""
Production engine for YieldTrace.

Handles:
- Production run planning & execution
- Bill of Materials (BOM) standard consumption calculations
- Usage variance tracking (actual vs planned consumption)
- Yield variance tracking (actual good packets vs standard expected packets)
- Packaging Reconciliation with mandatory AUDIT WARNING on discrepancy:
  Does NOT silently alter carton counts; records actual counts and triggers
  an explicit audit flag when unboxed packets or capacity mismatches occur.
- Append-only stock movements for raw materials issued, packaging consumed,
  and finished goods received into stock.
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
import math
from sqlalchemy.orm import Session

from app.models import (
    ProductionRun,
    RunConsumption,
    RunOutput,
    BOM,
    BOMLine,
    Item,
    Overhead,
    StockMoveType,
    StockMoveDirection,
    ProductionRunStatus,
    AuditLog
)
from app.modules.inventory.service import InventoryService


class ProductionService:
    def __init__(self, db: Session):
        self.db = db
        self.inventory_service = InventoryService(db)

    def calculate_planned_consumption(self, bom_id: int, planned_batches: float) -> List[Dict]:
        """
        Calculate planned quantities and standard costs according to BOM recipe.
        """
        bom = self.db.query(BOM).filter(BOM.id == bom_id).first()
        if not bom:
            raise ValueError(f"BOM with id {bom_id} not found")

        plans = []
        for line in bom.lines:
            # line.standard_quantity is per 1 batch
            planned_qty = line.standard_quantity * planned_batches
            std_cost = line.item.standard_cost
            plans.append({
                "item_id": line.item_id,
                "item_code": line.item.code,
                "item_name": line.item.name,
                "unit": line.unit,
                "planned_quantity": planned_qty,
                "standard_unit_cost": std_cost,
                "planned_total_cost": round(planned_qty * std_cost, 4)
            })
        return plans

    def record_production_run(
        self,
        run_number: str,
        bom_id: int,
        planned_batches: float,
        actual_consumptions: List[Dict],
        good_packets_produced: float,
        damaged_packets: float = 0.0,
        cartons_used: float = 0.0,
        carton_capacity: Optional[int] = None,
        overheads_data: Optional[List[Dict]] = None,
        notes: Optional[str] = None
    ) -> ProductionRun:
        """
        Execute and record a production run with:
        1. Material consumption & usage variances
        2. Good packets output & yield variance
        3. Packaging reconciliation & audit warnings
        4. Overhead allocation
        5. Append-only ledger updates (RAW/PACKAGING OUT, FINISHED GOODS IN)
        """
        bom = self.db.query(BOM).filter(BOM.id == bom_id).first()
        if not bom:
            raise ValueError(f"BOM {bom_id} not found")

        capacity = carton_capacity if carton_capacity is not None else (bom.pack_carton_capacity or 20)
        expected_packets = bom.yield_packets * planned_batches

        # Create production run
        run = ProductionRun(
            run_number=run_number,
            bom_id=bom_id,
            planned_batches=planned_batches,
            status=ProductionRunStatus.COMPLETED,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            notes=notes
        )
        self.db.add(run)
        self.db.flush()

        # 1. Process Consumptions
        # Map BOM standards for planned quantities
        bom_dict = {line.item_id: line for line in bom.lines}

        for actual_cons in actual_consumptions:
            item_id = actual_cons["item_id"]
            actual_qty = float(actual_cons["actual_quantity"])
            item = self.db.query(Item).filter(Item.id == item_id).first()
            if not item:
                raise ValueError(f"Item {item_id} not found")

            bom_line = bom_dict.get(item_id)
            if bom_line:
                planned_qty = bom_line.standard_quantity * planned_batches
                unit = bom_line.unit
            else:
                planned_qty = actual_cons.get("planned_quantity", actual_qty)
                unit = actual_cons.get("unit", item.unit)

            std_unit_cost = item.standard_cost or 0.0
            actual_unit_cost = item.current_wauc or std_unit_cost

            # Usage Variance = (Actual Qty - Planned Qty) * Standard Price
            usage_var_qty = round(actual_qty - planned_qty, 4)
            usage_var_cost = round(usage_var_qty * std_unit_cost, 4)

            rc = RunConsumption(
                run_id=run.id,
                item_id=item_id,
                planned_quantity=planned_qty,
                actual_quantity=actual_qty,
                unit=unit,
                standard_unit_cost=std_unit_cost,
                actual_unit_cost=actual_unit_cost,
                usage_variance_qty=usage_var_qty,
                usage_variance_cost=usage_var_cost
            )
            self.db.add(rc)

            # Append-only stock movement for material consumption
            move_type = (
                StockMoveType.PACKAGING_CONSUMPTION
                if item.category.value == "packaging"
                else StockMoveType.PRODUCTION_ISSUE
            )
            self.inventory_service.record_stock_move(
                item_id=item_id,
                move_type=move_type,
                direction=StockMoveDirection.OUT,
                quantity=actual_qty,
                unit=unit,
                unit_cost=actual_unit_cost,
                reference_type="production_run",
                reference_id=run_number,
                notes=f"Consumed in run {run_number}"
            )

        # 2. Packaging Reconciliation and Audit Warning Logic
        # Total capacity of the cartons available/used
        total_boxed_capacity = cartons_used * capacity
        packaging_mismatch = False
        audit_warning = None

        # Check if actual output packets match cartons exactly
        # If good packets != cartons_used * capacity, we have unboxed packets or mismatch
        unboxed_packets = max(0.0, good_packets_produced - total_boxed_capacity)

        if good_packets_produced != total_boxed_capacity:
            packaging_mismatch = True
            audit_warning = (
                f"Audit warning – packaging mismatch: Good packets produced ({good_packets_produced}) "
                f"does not match carton capacity ({total_boxed_capacity} packets across {cartons_used} cartons). "
                f"Unboxed packets: {int(unboxed_packets)}."
            )

        # 3. Output and Yield Variance
        finished_good = bom.finished_good
        fg_std_cost = finished_good.standard_cost if finished_good else 0.0
        yield_var_packets = round(expected_packets - good_packets_produced, 4)
        yield_var_cost = round(yield_var_packets * fg_std_cost, 4)

        ro = RunOutput(
            run_id=run.id,
            finished_good_id=bom.finished_good_id,
            planned_good_packets=expected_packets,
            actual_good_packets=good_packets_produced,
            damaged_packets=damaged_packets,
            unboxed_packets=unboxed_packets,
            cartons_used=cartons_used,
            carton_capacity=capacity,
            packaging_mismatch=packaging_mismatch,
            audit_warning=audit_warning,
            yield_variance_packets=yield_var_packets,
            yield_variance_cost=yield_var_cost
        )
        self.db.add(ro)

        # Append-only stock movement for finished goods produced
        if good_packets_produced > 0 and bom.finished_good_id:
            # Calculate actual unit cost based on consumed materials + overhead
            self.inventory_service.record_stock_move(
                item_id=bom.finished_good_id,
                move_type=StockMoveType.PRODUCTION_RECEIPT,
                direction=StockMoveDirection.IN,
                quantity=good_packets_produced,
                unit=finished_good.unit,
                unit_cost=fg_std_cost,
                reference_type="production_run",
                reference_id=run_number,
                notes=f"Produced in run {run_number}"
            )

        # 4. Overheads
        if overheads_data:
            for oh in overheads_data:
                overhead_entry = Overhead(
                    run_id=run.id,
                    category=oh.get("category", "labour"),
                    description=oh.get("description", ""),
                    amount=float(oh.get("amount", 0.0)),
                    allocation_method=oh.get("allocation_method", "direct_run")
                )
                self.db.add(overhead_entry)

        # 5. Audit Log if mismatch or run completed
        if packaging_mismatch:
            audit = AuditLog(
                table_name="production_runs",
                record_id=run_number,
                action="AUDIT_WARNING",
                changed_by="system",
                new_values=f"Good: {good_packets_produced}, Cartons: {cartons_used}, Capacity: {total_boxed_capacity}",
                notes=audit_warning
            )
            self.db.add(audit)

        self.db.commit()
        self.db.refresh(run)
        return run
