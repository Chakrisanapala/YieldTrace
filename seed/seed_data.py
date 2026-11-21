"""
NIT Benchmark Canonical Seed Data for YieldTrace.
NIT Tiruchirappalli — Winter Internship 2026.

Canonical Test Scenario:
1. Product: Murukku 200 g
2. Opening Inventory (via Append-Only Ledger):
   - Flour: 100 kg @ ₹40.00
   - Cooking oil: 30 litres @ ₹110.00
   - Spice mix: 5 kg @ ₹250.00
   - Printed pouches: 500 pieces @ ₹1.50
   - Cartons: 30 cartons @ ₹25.00
   - Finished Murukku 200 g: 50 packets @ ₹20.00
3. Milestone Purchase:
   - 60 kg Flour @ ₹45/kg = ₹2,700 (Invoice #INV-NIT-FLOUR-60)
   - Flour WAUC becomes ₹41.875/kg
   - Flour stock becomes 160 kg
4. Milestone Production Run:
   - Standard BOM: 200 packets requires 40 kg flour, 10 L oil, 1 kg spice mix, 200 pouches, 10 cartons
   - Actual Issued:
     * 40 kg flour
     * 10.5 L oil (+5.0% oil variance)
     * 1.2 kg spice mix (+20.0% variance)
     * 188 good packets produced (-6.0% yield variance)
     * 6 damaged pouches (500 - 188 - 6 = 306 pouches remaining)
     * 9 cartons issued (Preserved! 9 * 20 = 180 capacity vs 188 output -> 8 unboxed packets)
     * Packaging reconciliation warning generated
   - Overheads: Labour ₹1,200 + Gas/Electricity ₹600 = ₹1,800
5. Sales & Fulfillment:
   - Opening 50 + Produced 188 = 238 packets available
   - Retailer A (Tamil Nadu): Ordered 150 @ ₹50. Taxable ₹7,500. CGST 2.5% (₹187.50) + SGST 2.5% (₹187.50) = ₹7,875.
     Payment received: ₹4,000. Outstanding: ₹3,875.
     Dispatched 150 packets -> Remaining 88 packets.
   - Distributor B (Karnataka): Ordered 120 @ ₹50. IGST 5%.
     Available stock is 88 packets -> Fulfilled 88 packets, Shortage/Backorder: 32 packets.
     Dispatched 88 packets -> Remaining Finished Goods: 0 packets!
6. Canonical Closing Balances:
   - Flour: 120 kg
   - Cooking oil: 19.5 L
   - Spice mix: 3.8 kg
   - Pouches: 306
   - Cartons: 21
   - Finished goods after production: 238
   - Finished goods after Retailer A: 88
   - Finished goods after Distributor B: 0
"""
import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.models import (
    User, UserRole,
    Item, ItemCategory,
    UnitConversion,
    Supplier, Customer,
    BOM, BOMLine,
    Invoice,
    StockMoveType, StockMoveDirection
)
from app.modules.auth.service import AuthService
from app.modules.inventory.service import InventoryService
from app.modules.purchases.service import PurchaseService
from app.modules.production.service import ProductionService
from app.modules.sales.service import SalesService
from app.modules.insight.forensics_service import VarianceForensicsService


def seed_canonical_benchmark(db: Session) -> Dict:
    # Ensure all tables are recreated with current schema
    from app.database import engine, Base
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    auth_service = AuthService(db)
    inv_service = InventoryService(db)
    pur_service = PurchaseService(db)
    prod_service = ProductionService(db)
    sales_service = SalesService(db, supplier_state="Tamil Nadu")
    forensics_service = VarianceForensicsService(db)

    # 1. System Users across all 6 enterprise roles
    users = [
        {"username": "owner", "email": "owner@yieldtrace.local", "role": UserRole.OWNER, "name": "Managing Director"},
        {"username": "admin", "email": "admin@yieldtrace.local", "role": UserRole.ADMIN, "name": "System Administrator"},
        {"username": "sales_lead", "email": "sales@yieldtrace.local", "role": UserRole.SALESMAN, "name": "Ramesh Kumar (Sales)"},
        {"username": "prod_supervisor", "email": "prod@yieldtrace.local", "role": UserRole.PRODUCTION_SUPERVISOR, "name": "Suresh Raina (Plant Lead)"},
        {"username": "accountant", "email": "accounts@yieldtrace.local", "role": UserRole.ACCOUNTANT, "name": "Priya Sharma (Accounts)"},
        {"username": "auditor", "email": "auditor@yieldtrace.local", "role": UserRole.AUDITOR, "name": "Karthik CA (Statutory Auditor)"},
    ]
    for u in users:
        auth_service.register_user(
            username=u["username"],
            email=u["email"],
            password="Password@123",
            role=u["role"],
            full_name=u["name"]
        )

    # 2. Unit Conversions
    conversions = [
        UnitConversion(from_unit="kg", to_unit="g", multiplier=1000.0),
        UnitConversion(from_unit="g", to_unit="kg", multiplier=0.001),
        UnitConversion(from_unit="litre", to_unit="ml", multiplier=1000.0),
        UnitConversion(from_unit="carton", to_unit="packets", multiplier=20.0),
    ]
    db.add_all(conversions)
    db.flush()

    # 3. Suppliers & Customers
    supplier_flour = Supplier(
        code="SUP-FLOUR-01",
        name="Annapurna Agro Mills",
        gstin="33AAAAA0000A1Z5",
        state="Tamil Nadu",
        contact_phone="+91-9876543210",
        address="Tiruchirappalli, Tamil Nadu"
    )
    supplier_oil = Supplier(
        code="SUP-OIL-01",
        name="Bharat Edible Oils Ltd",
        gstin="33BBBBB1111B2Z6",
        state="Tamil Nadu",
        contact_phone="+91-9876543211",
        address="Madurai, Tamil Nadu"
    )
    supplier_pack = Supplier(
        code="SUP-PACK-01",
        name="Printech Polymers & Packaging",
        gstin="33CCCCC2222C3Z7",
        state="Tamil Nadu",
        contact_phone="+91-9876543212",
        address="Coimbatore, Tamil Nadu"
    )
    db.add_all([supplier_flour, supplier_oil, supplier_pack])

    # Retailer A (Tamil Nadu - Intra-State)
    retailer_a = Customer(
        code="CUST-RET-A",
        name="Retailer A (Heritage Stores)",
        customer_type="retailer",
        gstin="33DDDDD3333D4Z8",
        state="Tamil Nadu",
        contact_phone="+91-9443311223",
        address="Anna Nagar, Chennai, Tamil Nadu"
    )
    # Distributor B (Karnataka - Inter-State)
    distributor_b = Customer(
        code="CUST-DIST-B",
        name="Distributor B (Cauvery Wholesale)",
        customer_type="distributor",
        gstin="29EEEEE4444E5Z9",
        state="Karnataka",
        contact_phone="+91-9880055443",
        address="BTM Layout, Bengaluru, Karnataka"
    )
    db.add_all([retailer_a, distributor_b])
    db.flush()

    # 4. Item Master (Exact Canonical Benchmark Names & Units)
    flour = Item(
        code="RM-FLOUR",
        name="Flour",
        category=ItemCategory.RAW_MATERIAL,
        unit="kg",
        standard_cost=40.0,
        current_wauc=40.0,
        reorder_level=50.0
    )
    oil = Item(
        code="RM-OIL",
        name="Cooking oil",
        category=ItemCategory.RAW_MATERIAL,
        unit="litres",
        standard_cost=110.0,
        current_wauc=110.0,
        reorder_level=15.0
    )
    spice_mix = Item(
        code="RM-SPICE-MIX",
        name="Spice mix",
        category=ItemCategory.RAW_MATERIAL,
        unit="kg",
        standard_cost=250.0,
        current_wauc=250.0,
        reorder_level=5.0
    )
    pouches = Item(
        code="PK-POUCH-200G",
        name="Printed pouches",
        category=ItemCategory.PACKAGING,
        unit="pieces",
        standard_cost=1.50,
        current_wauc=1.50,
        reorder_level=200.0
    )
    cartons = Item(
        code="PK-CARTON-20PK",
        name="Cartons",
        category=ItemCategory.PACKAGING,
        unit="cartons",
        standard_cost=25.00,
        current_wauc=25.00,
        reorder_level=10.0
    )
    murukku_fg = Item(
        code="FG-MURUKKU-200G",
        name="Murukku 200 g",
        category=ItemCategory.FINISHED_GOOD,
        unit="packets",
        standard_cost=20.00,
        current_wauc=20.00,
        selling_price=50.00,
        gst_rate=5.0,
        reorder_level=100.0
    )
    db.add_all([flour, oil, spice_mix, pouches, cartons, murukku_fg])
    db.flush()

    # 5. Bill of Materials: Murukku 200 g (Standard Output: 200 packets)
    bom = BOM(
        finished_good_id=murukku_fg.id,
        code="BOM-MURUKKU-200G-V1",
        name="Standard Murukku 200g Recipe (200 Pkts)",
        version="1.0",
        batch_size=1.0,
        yield_packets=200.0,
        pack_carton_capacity=20,
        standard_overhead=1800.0,
        is_active=True
    )
    db.add(bom)
    db.flush()

    bom_lines = [
        BOMLine(bom_id=bom.id, item_id=flour.id, standard_quantity=40.0, unit="kg"),
        BOMLine(bom_id=bom.id, item_id=oil.id, standard_quantity=10.0, unit="litres"),
        BOMLine(bom_id=bom.id, item_id=spice_mix.id, standard_quantity=1.0, unit="kg"),
        BOMLine(bom_id=bom.id, item_id=pouches.id, standard_quantity=200.0, unit="pieces"),
        BOMLine(bom_id=bom.id, item_id=cartons.id, standard_quantity=10.0, unit="cartons"),
    ]
    db.add_all(bom_lines)
    db.commit()

    # 6. Canonical Initial Stock Injection (Strictly via Append-Only Ledger)
    inv_service.record_stock_move(flour.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 100.0, "kg", 40.0, "initial_stock", "INIT-FLOUR", "Initial stock")
    inv_service.record_stock_move(oil.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 30.0, "litres", 110.0, "initial_stock", "INIT-OIL", "Initial stock")
    inv_service.record_stock_move(spice_mix.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 5.0, "kg", 250.0, "initial_stock", "INIT-SPICE", "Initial stock")
    inv_service.record_stock_move(pouches.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 500.0, "pieces", 1.50, "initial_stock", "INIT-POUCH", "Initial stock")
    inv_service.record_stock_move(cartons.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 30.0, "cartons", 25.00, "initial_stock", "INIT-CARTON", "Initial stock")
    inv_service.record_stock_move(murukku_fg.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 50.0, "packets", 20.00, "initial_stock", "INIT-MURUKKU", "Opening finished stock")
    db.commit()

    # 7. Milestone Purchase: 60 kg Flour at ₹45/kg
    pur_service.record_purchase(
        invoice_no="INV-NIT-FLOUR-60",
        supplier_id=supplier_flour.id,
        lines_data=[{"item_id": flour.id, "quantity": 60.0, "unit": "kg", "unit_price": 45.0}],
        idempotency_token="IDEM-PUR-FLOUR-001",
        notes="NIT Benchmark: 60 kg flour @ ₹45/kg (Total ₹2,700)"
    )

    # 8. Milestone Production Batch (Planned 200 packets -> Actual 188 good packets)
    prod_run = prod_service.record_production_run(
        run_number="RUN-NIT-MURUKKU-001",
        bom_id=bom.id,
        planned_batches=1.0,
        actual_consumptions=[
            {"item_id": flour.id, "actual_quantity": 40.0, "unit": "kg"},
            {"item_id": oil.id, "actual_quantity": 10.5, "unit": "litres"},      # +5.0% oil variance
            {"item_id": spice_mix.id, "actual_quantity": 1.2, "unit": "kg"},     # +20.0% variance
            {"item_id": pouches.id, "actual_quantity": 194.0, "unit": "pieces"}, # 188 good + 6 damaged = 194 consumed
            {"item_id": cartons.id, "actual_quantity": 9.0, "unit": "cartons"},  # 9 cartons issued (Preserved!)
        ],
        good_packets_produced=188.0,
        damaged_packets=6.0,
        damaged_pouches=6.0,
        cartons_used=9.0,
        carton_capacity=20,
        overheads_data=[
            {"category": "labour", "description": "Frying & packing operators", "amount": 1200.0},
            {"category": "gas_electricity", "description": "Commercial LPG & sealing power", "amount": 600.0}
        ],
        supervisor="Suresh Raina (Plant Lead)",
        batch_reference="BATCH-NIT-MURUKKU-2026-01",
        is_synthetic=False,
        notes="NIT Benchmark Murukku 200g Production Run"
    )

    # Run Variance Forensics Investigation on Benchmark Run
    forensics_service.investigate_production_run(prod_run.id)

    # Check Stock after Production (Murukku FG must be 50 opening + 188 produced = 238 packets)
    fg_after_prod = inv_service.get_stock_balance(murukku_fg.id)

    # 9. Sales: Retailer A (Tamil Nadu)
    # Order: 150 packets @ ₹50.00
    order_a = sales_service.create_sales_order(
        order_number="SO-RET-A-001",
        customer_id=retailer_a.id,
        lines_data=[{"item_id": murukku_fg.id, "ordered_quantity": 150.0, "unit_price": 50.0}],
        notes="NIT Benchmark Retailer A Order"
    )
    sales_service.approve_order(order_a.id)
    disp_a_res = sales_service.dispatch_order(order_a.id, notes="Retailer A Full Dispatch")

    # Payment: Retailer A pays ₹4,000 on ₹7,875 invoice
    inv_a = db.query(Invoice).filter(Invoice.order_id == order_a.id).first()
    sales_service.record_payment(
        invoice_id=inv_a.id,
        amount=4000.0,
        payment_mode="BANK_TRANSFER",
        reference_no="UTR-RET-A-4000",
        notes="Part payment of ₹4,000 against ₹7,875"
    )

    fg_after_ret_a = inv_service.get_stock_balance(murukku_fg.id)

    # 10. Sales: Distributor B (Karnataka - Inter-state)
    # Order: 120 packets @ ₹50.00. Available stock is only 88 packets!
    order_b = sales_service.create_sales_order(
        order_number="SO-DIST-B-001",
        customer_id=distributor_b.id,
        lines_data=[{"item_id": murukku_fg.id, "ordered_quantity": 120.0, "unit_price": 50.0}],
        notes="NIT Benchmark Distributor B Order (Karnataka)"
    )
    sales_service.approve_order(order_b.id)
    disp_b_res = sales_service.dispatch_order(order_b.id, notes="Distributor B Partial Dispatch (88 fulfilled, 32 shortage)")

    fg_after_dist_b = inv_service.get_stock_balance(murukku_fg.id)

    # 11. Final Balances Map
    final_balances = {
        "Flour": inv_service.get_stock_balance(flour.id),
        "Cooking oil": inv_service.get_stock_balance(oil.id),
        "Spice mix": inv_service.get_stock_balance(spice_mix.id),
        "Pouches": inv_service.get_stock_balance(pouches.id),
        "Cartons": inv_service.get_stock_balance(cartons.id),
        "Finished Goods after Production": fg_after_prod,
        "Finished Goods after Retailer A": fg_after_ret_a,
        "Finished Goods after Distributor B": fg_after_dist_b,
    }

    print("\n=======================================================")
    print("NIT BENCHMARK SEED COMPLETED SUCCESSFULLY")
    print("=======================================================")
    for k, v in final_balances.items():
        print(f"  {k:35}: {v}")
    print("=======================================================\n")

    return final_balances


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_canonical_benchmark(db)
    finally:
        db.close()
