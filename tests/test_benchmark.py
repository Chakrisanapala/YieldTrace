"""
Automated correctness tests for Day 1 NIT Benchmark Steps 1–3.

SUCCESS CONDITION:
When we record the NIT benchmark purchase and production run,
YieldTrace must calculate:
- 120 kg flour
- 19.5 litres oil
- 306 pouches
- 21 cartons
- 238 finished packets
with the packaging reconciliation warning and mathematically reconciled cost waterfall.
"""
import pytest
from app.models import Item, BOM, Supplier, AuditLog
from app.modules.inventory.service import InventoryService
from app.modules.purchases.service import PurchaseService
from app.modules.production.service import ProductionService
from app.modules.costing.service import CostingService


def test_nit_benchmark_milestone(seeded_benchmark_db):
    db = seeded_benchmark_db
    inv_service = InventoryService(db)
    purchase_service = PurchaseService(db)
    production_service = ProductionService(db)
    costing_service = CostingService(db)

    # Fetch items
    flour = db.query(Item).filter(Item.code == "RM-FLOUR").first()
    oil = db.query(Item).filter(Item.code == "RM-OIL").first()
    pouch = db.query(Item).filter(Item.code == "PK-POUCH-200G").first()
    carton = db.query(Item).filter(Item.code == "PK-CARTON-20PK").first()
    finished_good = db.query(Item).filter(Item.code == "FG-SNACK-200G").first()
    supplier = db.query(Supplier).filter(Supplier.code == "SUP-FLOUR-01").first()
    bom = db.query(BOM).filter(BOM.code == "BOM-SNACK-200G").first()

    # ----------------------------------------------------
    # Verification: Initial State
    # ----------------------------------------------------
    assert inv_service.get_stock_balance(flour.id) == 100.0
    assert inv_service.get_stock_balance(oil.id) == 25.0
    assert inv_service.get_stock_balance(pouch.id) == 550.0
    assert inv_service.get_stock_balance(carton.id) == 32.0
    assert inv_service.get_stock_balance(finished_good.id) == 0.0

    # ----------------------------------------------------
    # Benchmark Step 1: Purchase 60 kg flour at ₹45/kg
    # ----------------------------------------------------
    purchase = purchase_service.record_purchase(
        invoice_no="INV-NIT-FLOUR-60",
        supplier_id=supplier.id,
        lines_data=[
            {
                "item_id": flour.id,
                "quantity": 60.0,
                "unit": "kg",
                "unit_price": 45.0
            }
        ],
        notes="NIT Milestone Purchase"
    )

    # Check purchase details & price variance
    assert len(purchase.lines) == 1
    p_line = purchase.lines[0]
    # Price Variance = (45 - 40 std) * 60 = ₹300
    assert p_line.price_variance == 300.0
    # Weighted Average Unit Cost (WAUC) = (100*40 + 60*45) / 160 = 41.875
    db.refresh(flour)
    assert flour.current_wauc == 41.875
    # Flour stock after purchase must be 160 kg
    assert inv_service.get_stock_balance(flour.id) == 160.0

    # ----------------------------------------------------
    # Benchmark Step 2: Record Production Run
    # ----------------------------------------------------
    # Consumptions:
    # - 40 kg flour
    # - 5.5 litres oil
    # - 244 pouches (238 good + 6 damaged)
    # - 11 cartons used
    # Good output: 238 finished packets
    # Overheads: Labour 650, Power 220, Gas 380
    run = production_service.record_production_run(
        run_number="RUN-NIT-BENCHMARK-001",
        bom_id=bom.id,
        planned_batches=1.0,
        actual_consumptions=[
            {"item_id": flour.id, "actual_quantity": 40.0, "unit": "kg"},
            {"item_id": oil.id, "actual_quantity": 5.5, "unit": "litres"},
            {"item_id": pouch.id, "actual_quantity": 244.0, "unit": "pieces"},
            {"item_id": carton.id, "actual_quantity": 11.0, "unit": "cartons"},
        ],
        good_packets_produced=238.0,
        damaged_packets=6.0,
        cartons_used=11.0,
        carton_capacity=20,
        overheads_data=[
            {"category": "labour", "amount": 650.0},
            {"category": "power", "amount": 220.0},
            {"category": "gas", "amount": 380.0}
        ],
        notes="NIT Benchmark Production Run"
    )

    # ----------------------------------------------------
    # Verification: Packaging Reconciliation Warning
    # ----------------------------------------------------
    ro = run.output
    assert ro.actual_good_packets == 238.0
    assert ro.cartons_used == 11.0
    assert ro.carton_capacity == 20
    # 11 cartons * 20 capacity = 220 packets. Unboxed = 238 - 220 = 18 packets
    assert ro.unboxed_packets == 18.0
    assert ro.packaging_mismatch is True
    assert "Audit warning – packaging mismatch" in ro.audit_warning
    assert "Unboxed packets: 18" in ro.audit_warning

    # Check audit logs for recorded warning
    warning_audit = (
        db.query(AuditLog)
        .filter(AuditLog.record_id == "RUN-NIT-BENCHMARK-001", AuditLog.action == "AUDIT_WARNING")
        .first()
    )
    assert warning_audit is not None

    # ----------------------------------------------------
    # CORE SUCCESS CONDITION: Stock Balances from Ledger
    # YieldTrace must calculate:
    # 120 kg flour, 19.5 litres oil, 306 pouches, 21 cartons, 238 finished packets
    # ----------------------------------------------------
    bal_flour = inv_service.get_stock_balance(flour.id)
    bal_oil = inv_service.get_stock_balance(oil.id)
    bal_pouch = inv_service.get_stock_balance(pouch.id)
    bal_carton = inv_service.get_stock_balance(carton.id)
    bal_fg = inv_service.get_stock_balance(finished_good.id)

    assert bal_flour == 120.0, f"Expected 120 kg flour, got {bal_flour}"
    assert bal_oil == 19.5, f"Expected 19.5 litres oil, got {bal_oil}"
    assert bal_pouch == 306.0, f"Expected 306 pouches, got {bal_pouch}"
    assert bal_carton == 21.0, f"Expected 21 cartons, got {bal_carton}"
    assert bal_fg == 238.0, f"Expected 238 finished packets, got {bal_fg}"

    # ----------------------------------------------------
    # Verification: Cost Waterfall & Forensics
    # ----------------------------------------------------
    costing = costing_service.calculate_cost_waterfall(run.id)
    assert costing["is_mathematically_reconciled"] is True
    assert costing["total_overheads"] == 1250.0  # 650 + 220 + 380
    assert costing["yield_loss_packets"] == 12.0 # 250 expected - 238 good
    assert costing["total_actual_production_cost"] > 0
