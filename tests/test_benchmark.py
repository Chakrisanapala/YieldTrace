"""
Exhaustive Automated Verification Suite for Canonical NIT Benchmark.
NIT Tiruchirappalli — Winter Internship 2026.

Validates:
1. Canonical Initial Stock:
   - Flour: 100 kg
   - Cooking oil: 30 litres
   - Spice mix: 5 kg
   - Printed pouches: 500 pieces
   - Cartons: 30 cartons
   - Finished Murukku 200 g: 50 packets
2. Benchmark Purchase:
   - 60 kg Flour @ ₹45/kg = ₹2,700
   - Price Variance: ₹300
   - New WAUC: ₹41.875/kg
   - Available Flour: 160 kg
3. Benchmark Production Run:
   - 40 kg flour, 10.5 L oil (+5.0% oil variance), 1.2 kg spice mix
   - 188 good packets produced (-6.0% yield variance)
   - 6 damaged pouches
   - 9 cartons issued (180 boxed capacity, 8 unboxed packets)
   - Packaging reconciliation warning generated
   - Preserves 9 cartons without silent modification
4. Cost Waterfall Reconciliation:
   - Standard BOM baseline + Price Var + Usage Var + Overhead Var = Actual Cost (0.00 discrepancy)
5. Sales & Dispatches:
   - Retailer A (Tamil Nadu): 150 packets, ₹7,875 (CGST ₹187.50, SGST ₹187.50), Paid ₹4,000, Outstanding ₹3,875
   - Distributor B (Karnataka): 120 packets ordered, 88 fulfilled, 32 shortage/backorder, 0 negative stock
6. Exact Closing Stock Balances:
   - Flour: 120 kg
   - Cooking oil: 19.5 L
   - Spice mix: 3.8 kg
   - Pouches: 306
   - Cartons: 21
   - Finished goods after production: 238 packets
   - Finished goods after Retailer A: 88 packets
   - Finished goods after Distributor B: 0 packets
"""
import pytest
from app.models import Item, BOM, Supplier, Customer, Invoice, AuditLog
from app.modules.inventory.service import InventoryService
from app.modules.purchases.service import PurchaseService
from app.modules.production.service import ProductionService
from app.modules.sales.service import SalesService
from app.modules.costing.service import CostingService


def test_canonical_nit_benchmark_complete_flow(canonical_benchmark_setup):
    db = canonical_benchmark_setup
    inv = InventoryService(db)
    pur = PurchaseService(db)
    prod = ProductionService(db)
    sales = SalesService(db, supplier_state="Tamil Nadu")
    costing = CostingService(db)

    # 1. Fetch Item Records
    flour = db.query(Item).filter(Item.code == "RM-FLOUR").first()
    oil = db.query(Item).filter(Item.code == "RM-OIL").first()
    spice = db.query(Item).filter(Item.code == "RM-SPICE-MIX").first()
    pouches = db.query(Item).filter(Item.code == "PK-POUCH-200G").first()
    cartons = db.query(Item).filter(Item.code == "PK-CARTON-20PK").first()
    murukku = db.query(Item).filter(Item.code == "FG-MURUKKU-200G").first()

    sup = db.query(Supplier).filter(Supplier.code == "SUP-FLOUR-01").first()
    ret_a = db.query(Customer).filter(Customer.code == "CUST-RET-A").first()
    dist_b = db.query(Customer).filter(Customer.code == "CUST-DIST-B").first()
    bom = db.query(BOM).filter(BOM.code == "BOM-MURUKKU-200G-V1").first()

    # ----------------------------------------------------
    # Verification 1: Initial Stock
    # ----------------------------------------------------
    assert inv.get_stock_balance(flour.id) == 100.0
    assert inv.get_stock_balance(oil.id) == 30.0
    assert inv.get_stock_balance(spice.id) == 5.0
    assert inv.get_stock_balance(pouches.id) == 500.0
    assert inv.get_stock_balance(cartons.id) == 30.0
    assert inv.get_stock_balance(murukku.id) == 50.0

    # ----------------------------------------------------
    # Verification 2: Purchase 60 kg Flour at ₹45/kg
    # ----------------------------------------------------
    purchase = pur.record_purchase(
        invoice_no="INV-NIT-FLOUR-60",
        supplier_id=sup.id,
        lines_data=[{"item_id": flour.id, "quantity": 60.0, "unit": "kg", "unit_price": 45.0}],
        idempotency_token="TOKEN-NIT-PO-01"
    )
    assert purchase.total_amount == 2700.0
    assert purchase.lines[0].price_variance == 300.0  # (45 - 40) * 60 = 300
    db.refresh(flour)
    assert flour.current_wauc == 41.875  # (100*40 + 60*45) / 160 = 41.875
    assert inv.get_stock_balance(flour.id) == 160.0

    # ----------------------------------------------------
    # Verification 3: Production Batch (Planned 200 -> Actual 188)
    # ----------------------------------------------------
    run = prod.record_production_run(
        run_number="RUN-NIT-MURUKKU-001",
        bom_id=bom.id,
        planned_batches=1.0,
        actual_consumptions=[
            {"item_id": flour.id, "actual_quantity": 40.0, "unit": "kg"},
            {"item_id": oil.id, "actual_quantity": 10.5, "unit": "litres"},
            {"item_id": spice.id, "actual_quantity": 1.2, "unit": "kg"},
            {"item_id": pouches.id, "actual_quantity": 194.0, "unit": "pieces"},  # 188 good + 6 damaged
            {"item_id": cartons.id, "actual_quantity": 9.0, "unit": "cartons"},   # 9 cartons issued
        ],
        good_packets_produced=188.0,
        damaged_packets=6.0,
        damaged_pouches=6.0,
        cartons_used=9.0,
        carton_capacity=20,
        overheads_data=[
            {"category": "labour", "amount": 1200.0},
            {"category": "gas_electricity", "amount": 600.0}
        ],
        notes="NIT Murukku Benchmark Run"
    )

    ro = run.output
    assert ro.actual_good_packets == 188.0
    assert ro.damaged_pouches == 6.0
    assert ro.cartons_used == 9.0
    assert ro.carton_capacity == 20
    assert ro.unboxed_packets == 8.0  # 188 - (9 * 20) = 8
    assert ro.packaging_mismatch is True
    assert "Unboxed packets: 8" in ro.audit_warning
    assert ro.yield_variance_percentage == -6.0  # (188 - 200)/200 * 100 = -6.0%

    # Verify Oil Variance in consumptions: Planned 10.0L, Actual 10.5L -> +5.0%
    oil_cons = next(c for c in run.consumptions if c.item_id == oil.id)
    assert oil_cons.variance_percentage == 5.0
    assert oil_cons.usage_variance_qty == 0.5

    # Verify Spice Mix Variance: Planned 1.0kg, Actual 1.2kg -> +20.0%
    spice_cons = next(c for c in run.consumptions if c.item_id == spice.id)
    assert spice_cons.variance_percentage == 20.0
    assert spice_cons.usage_variance_qty == 0.2

    # Verify audit warning exists in audit_logs
    warning_log = db.query(AuditLog).filter(
        AuditLog.record_id == "RUN-NIT-MURUKKU-001",
        AuditLog.action == "AUDIT_WARNING"
    ).first()
    assert warning_log is not None

    # Check Finished Goods stock after production: Opening 50 + Produced 188 = 238
    assert inv.get_stock_balance(murukku.id) == 238.0

    # ----------------------------------------------------
    # Verification 4: Cost Waterfall Mathematical Reconciliation
    # ----------------------------------------------------
    cw = costing.calculate_cost_waterfall(run.id)
    assert cw["is_mathematically_reconciled"] is True
    assert cw["reconciliation_discrepancy"] == 0.00
    assert cw["standard_overhead"] == 1800.0
    assert cw["actual_overhead"] == 1800.0
    assert cw["overhead_variance"] == 0.0

    # ----------------------------------------------------
    # Verification 5: Sales Order Retailer A (Tamil Nadu - Intra-State)
    # ----------------------------------------------------
    order_a = sales.create_sales_order("SO-RET-A", ret_a.id, [{"item_id": murukku.id, "ordered_quantity": 150.0, "unit_price": 50.0}])
    sales.approve_order(order_a.id)
    disp_a = sales.dispatch_order(order_a.id)

    inv_a = db.query(Invoice).filter(Invoice.order_id == order_a.id).first()
    assert inv_a.is_interstate is False
    assert inv_a.taxable_amount == 7500.0
    assert inv_a.cgst_amount == 187.50
    assert inv_a.sgst_amount == 187.50
    assert inv_a.igst_amount == 0.0
    assert inv_a.total_amount == 7875.0

    # Payment: ₹4,000 received
    sales.record_payment(inv_a.id, 4000.0)
    db.refresh(inv_a)
    assert inv_a.paid_amount == 4000.0
    assert round(inv_a.total_amount - inv_a.paid_amount, 2) == 3875.0

    # Finished Goods balance after Retailer A: 238 - 150 = 88 packets
    assert inv.get_stock_balance(murukku.id) == 88.0

    # ----------------------------------------------------
    # Verification 6: Sales Order Distributor B (Karnataka - Inter-State & Shortage)
    # ----------------------------------------------------
    order_b = sales.create_sales_order("SO-DIST-B", dist_b.id, [{"item_id": murukku.id, "ordered_quantity": 120.0, "unit_price": 50.0}])
    sales.approve_order(order_b.id)
    disp_b = sales.dispatch_order(order_b.id)

    assert disp_b["total_ordered"] == 120.0
    assert disp_b["total_fulfilled"] == 88.0
    assert disp_b["total_backordered"] == 32.0  # Exact shortage recorded!

    inv_b = db.query(Invoice).filter(Invoice.order_id == order_b.id).first()
    assert inv_b.is_interstate is True
    assert inv_b.taxable_amount == 4400.0  # 88 * 50
    assert inv_b.igst_amount == 220.0      # 5% of 4400
    assert inv_b.total_amount == 4620.0

    # ----------------------------------------------------
    # Verification 7: Canonical Final Closing Balances
    # ----------------------------------------------------
    assert inv.get_stock_balance(flour.id) == 120.0, "Flour balance must be 120 kg"
    assert inv.get_stock_balance(oil.id) == 19.5, "Cooking oil balance must be 19.5 L"
    assert inv.get_stock_balance(spice.id) == 3.8, "Spice mix balance must be 3.8 kg"
    assert inv.get_stock_balance(pouches.id) == 306.0, "Printed pouches balance must be 306"
    assert inv.get_stock_balance(cartons.id) == 21.0, "Cartons balance must be 21"
    assert inv.get_stock_balance(murukku.id) == 0.0, "Finished goods balance after fulfillment must be 0"
