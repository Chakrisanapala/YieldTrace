"""
Unit tests for Intelligent Deterministic Production Planner.
"""
import pytest
from app.models import Item, BOM
from app.modules.insight.planner_service import ProductionPlannerService


def test_deterministic_production_planner_feasible(canonical_benchmark_setup):
    """Test feasibility when sufficient raw materials exist."""
    db = canonical_benchmark_setup
    planner = ProductionPlannerService(db)

    murukku = db.query(Item).filter(Item.code == "FG-MURUKKU-200G").first()

    # Demand: 150 packets. Current FG: 50 packets. Net shortage: 100 packets.
    # Batch size: 200 packets -> Required batches: CEILING(100/200) = 1 batch.
    plan = planner.plan_production_for_demand(murukku.id, target_demand_quantity=150.0)

    assert plan["gross_demand"] == 150.0
    assert plan["available_finished_stock"] == 50.0
    assert plan["net_shortage"] == 100.0
    assert plan["required_batches"] == 1
    assert plan["planned_production_output"] == 200.0
    assert plan["is_plan_feasible"] is True
    assert len(plan["procurement_shortages"]) == 0


def test_deterministic_production_planner_deficit(canonical_benchmark_setup):
    """Test planner identifying raw material deficit when stock is insufficient."""
    db = canonical_benchmark_setup
    planner = ProductionPlannerService(db)

    murukku = db.query(Item).filter(Item.code == "FG-MURUKKU-200G").first()

    # Demand: 2,000 packets. Required batches: CEILING(1950/200) = 10 batches.
    # 10 batches requires 400 kg flour, but only 100 kg available -> Deficit = 300 kg!
    plan = planner.plan_production_for_demand(murukku.id, target_demand_quantity=2000.0)

    assert plan["required_batches"] == 10
    assert plan["is_plan_feasible"] is False
    assert len(plan["procurement_shortages"]) > 0

    flour_shortage = next(s for s in plan["procurement_shortages"] if s["item_code"] == "RM-FLOUR")
    assert flour_shortage["required_quantity"] == 400.0
    assert flour_shortage["shortage_quantity"] == 300.0  # 400 - 100
