"""
Deterministic Intelligent Production Planner for YieldTrace.

Calculates:
1. Demand Aggregation: Outstanding unfulfilled customer orders.
2. Net Shortage: Required finished units - Live available finished stock.
3. Batch Sizing: Required batches = CEILING(Net Shortage / Standard Batch Output).
4. Material Feasibility:
   Checks current warehouse inventory for all BOM recipe components.
   Calculates required quantity per material.
   Determines whether plan is immediately feasible or blocked by stock shortages.
5. Procurement Advice:
   If infeasible, calculates the exact procurement shortfall by raw/packaging material.
"""
import math
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models import Item, BOM, BOMLine, SalesOrder, OrderStatus
from app.modules.inventory.service import InventoryService


class ProductionPlannerService:
    def __init__(self, db: Session):
        self.db = db
        self.inventory_service = InventoryService(db)

    def plan_production_for_demand(
        self,
        finished_good_id: int,
        target_demand_quantity: Optional[float] = None
    ) -> Dict:
        """
        Evaluate production requirements and material feasibility.
        If target_demand_quantity is not specified, sums pending demand from open sales orders.
        """
        finished_good = self.db.query(Item).filter(Item.id == finished_good_id).first()
        if not finished_good:
            raise ValueError(f"Finished Good #{finished_good_id} not found.")

        bom = self.db.query(BOM).filter(BOM.finished_good_id == finished_good_id, BOM.is_active == True).first()
        if not bom:
            raise ValueError(f"No active Bill of Materials found for '{finished_good.name}'.")

        # 1. Determine gross demand
        if target_demand_quantity is not None:
            gross_demand = float(target_demand_quantity)
        else:
            # Sum unfulfilled orders
            open_orders = (
                self.db.query(SalesOrder)
                .filter(SalesOrder.status.in_([OrderStatus.APPROVED, OrderStatus.PARTIALLY_FULFILLED, OrderStatus.DRAFT]))
                .all()
            )
            gross_demand = 0.0
            for o in open_orders:
                for line in o.lines:
                    if line.item_id == finished_good_id:
                        unfulfilled = line.ordered_quantity - line.fulfilled_quantity
                        gross_demand += max(0.0, unfulfilled)

        # 2. Live Finished Goods Inventory
        available_fg = max(0.0, self.inventory_service.get_stock_balance(finished_good_id))

        # 3. Net Shortage & Required Batches
        net_shortage = max(0.0, gross_demand - available_fg)

        batch_output = bom.yield_packets or 200.0
        if net_shortage > 0:
            required_batches = math.ceil(net_shortage / batch_output)
        else:
            required_batches = 0

        planned_production_output = required_batches * batch_output

        # 4. Material Feasibility Check
        material_feasibility = []
        is_plan_feasible = True
        procurement_shortages = []

        for line in bom.lines:
            mat = line.item
            req_qty = round(line.standard_quantity * required_batches, 4)
            curr_stock = max(0.0, self.inventory_service.get_stock_balance(mat.id))
            is_sufficient = curr_stock >= req_qty
            deficit = max(0.0, round(req_qty - curr_stock, 4))

            if not is_sufficient:
                is_plan_feasible = False
                procurement_shortages.append({
                    "item_id": mat.id,
                    "item_code": mat.code,
                    "item_name": mat.name,
                    "required_quantity": req_qty,
                    "available_quantity": curr_stock,
                    "shortage_quantity": deficit,
                    "unit": line.unit,
                    "estimated_purchase_cost": round(deficit * (mat.current_wauc or mat.standard_cost), 2)
                })

            material_feasibility.append({
                "item_id": mat.id,
                "item_code": mat.code,
                "item_name": mat.name,
                "category": mat.category.value,
                "standard_quantity_per_batch": line.standard_quantity,
                "total_required_quantity": req_qty,
                "current_stock_available": curr_stock,
                "is_sufficient": is_sufficient,
                "shortage": deficit,
                "unit": line.unit
            })

        return {
            "finished_good_id": finished_good.id,
            "product_name": finished_good.name,
            "bom_code": bom.code,
            "bom_version": bom.version,
            "gross_demand": gross_demand,
            "available_finished_stock": available_fg,
            "net_shortage": net_shortage,
            "batch_standard_output": batch_output,
            "required_batches": required_batches,
            "planned_production_output": planned_production_output,
            "surplus_after_production": max(0.0, (available_fg + planned_production_output) - gross_demand),
            "is_plan_feasible": is_plan_feasible,
            "material_feasibility": material_feasibility,
            "procurement_shortages": procurement_shortages,
            "recommendation": (
                f"Production feasible for {required_batches} batch(es) to produce {planned_production_output} units."
                if is_plan_feasible else
                f"Production BLOCKED for {required_batches} batch(es). Procure identified raw materials before issuing run."
            )
        }
