"""
NIT Benchmark Seed Data for YieldTrace.

Sets up:
1. Users & Roles (Admin, Production Manager, Auditor, Salesman)
2. Unit conversions (kg <-> g, litre <-> ml, carton <-> piece)
3. Suppliers & Customers
4. Item Master:
   - Flour (RAW_MATERIAL, kg, std_cost: 40.0)
   - Oil (RAW_MATERIAL, litres, std_cost: 110.0)
   - Snack Pouch 200g (PACKAGING, pieces, std_cost: 1.50)
   - Master Carton (PACKAGING, cartons, std_cost: 25.00, capacity: 20 packets)
   - Fried Snack 200g (FINISHED_GOOD, packets, std_cost: 18.50)
5. Standard BOM:
   - 1 Batch produces standard 250 packets
   - Standard Flour: 40 kg (0.16 kg/packet)
   - Standard Oil: 5.0 litres (0.02 L/packet)
   - Standard Pouches: 250 pieces (1 piece/packet)
   - Standard Cartons: 12.5 cartons (20 packets/carton)
6. Benchmark Scenario Execution:
   - Initial Stock:
     * Flour: 100 kg @ ₹40/kg
     * Oil: 25.0 litres @ ₹110/L
     * Pouches: 550 pieces @ ₹1.50/piece
     * Cartons: 32 cartons @ ₹25.00/carton
   - Benchmark Purchase:
     * 60 kg Flour @ ₹45/kg (Invoice #PO-NIT-001)
     * Total Flour available becomes 160 kg.
     * New WAUC = (100*40 + 60*45) / 160 = ₹41.875/kg.
   - Benchmark Production Run (#RUN-NIT-2026-001):
     * Consumes:
       - 40 kg Flour -> Remaining Stock: 160 - 40 = 120 kg
       - 5.5 litres Oil -> Remaining Stock: 25 - 5.5 = 19.5 litres
       - 244 Pouches (238 good + 6 damaged) -> Remaining Stock: 550 - 244 = 306 pouches
       - 11 Cartons -> Remaining Stock: 32 - 11 = 21 cartons
     * Produces:
       - 238 Good Packets -> Finished Good Stock: 238 packets
     * Packaging Reconciliation:
       - 11 Cartons used * 20 capacity = 220 packets
       - Good packets produced = 238 packets
       - Unboxed packets = 18
       - Audit Warning triggered: Packaging mismatch!
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.models import (
    User, UserRole,
    Item, ItemCategory,
    UnitConversion,
    Supplier, Customer,
    BOM, BOMLine,
    StockMoveType, StockMoveDirection
)
from app.modules.inventory.service import InventoryService
from app.modules.purchases.service import PurchaseService
from app.modules.production.service import ProductionService


def seed_all(db: Session):
    init_db()

    # Clear existing data for fresh seed (in reverse dependency order)
    # SQLite foreign keys enabled
    from app.models import (
        StockMove, RunConsumption, RunOutput, Overhead,
        ProductionRun, PurchaseLine, Purchase, BOMLine, BOM,
        AuditLog, UnitConversion, Supplier, Customer, Item, User
    )
    for model in [StockMove, RunConsumption, RunOutput, Overhead, ProductionRun,
                  PurchaseLine, Purchase, BOMLine, BOM, AuditLog,
                  UnitConversion, Supplier, Customer, Item, User]:
        db.query(model).delete()
    db.commit()

    inventory_service = InventoryService(db)
    purchase_service = PurchaseService(db)
    production_service = ProductionService(db)

    # 1. Users
    users = [
        User(username="admin", email="admin@yieldtrace.local", hashed_password="hashed_admin_pass", role=UserRole.ADMIN),
        User(username="production_lead", email="prod@yieldtrace.local", hashed_password="hashed_prod_pass", role=UserRole.PRODUCTION),
        User(username="auditor", email="auditor@yieldtrace.local", hashed_password="hashed_audit_pass", role=UserRole.AUDITOR),
        User(username="sales_rep", email="sales@yieldtrace.local", hashed_password="hashed_sales_pass", role=UserRole.SALESMAN),
    ]
    db.add_all(users)
    db.flush()

    # 2. Unit Conversions
    conversions = [
        UnitConversion(from_unit="kg", to_unit="g", multiplier=1000.0),
        UnitConversion(from_unit="g", to_unit="kg", multiplier=0.001),
        UnitConversion(from_unit="litre", to_unit="ml", multiplier=1000.0),
        UnitConversion(from_unit="carton", to_unit="pieces", multiplier=20.0),
    ]
    db.add_all(conversions)
    db.flush()

    # 3. Suppliers & Customers
    supplier_flour = Supplier(name="Annapurna Agro Mills", code="SUP-FLOUR-01", contact_phone="+91-9876543210")
    supplier_oil = Supplier(name="Bharat Edible Oils Ltd", code="SUP-OIL-01", contact_phone="+91-9876543211")
    supplier_pack = Supplier(name="Printech Polymers & Packaging", code="SUP-PACK-01", contact_phone="+91-9876543212")
    db.add_all([supplier_flour, supplier_oil, supplier_pack])

    customer_1 = Customer(name="Heritage Supermarkets", code="CUST-RET-01", customer_type="retailer")
    customer_2 = Customer(name="Metro North Distributors", code="CUST-DIST-01", customer_type="distributor")
    db.add_all([customer_1, customer_2])
    db.flush()

    # 4. Item Master
    flour = Item(
        code="RM-FLOUR",
        name="Refined Wheat Flour (Maida)",
        category=ItemCategory.RAW_MATERIAL,
        unit="kg",
        standard_cost=40.0,
        current_wauc=40.0,
        reorder_level=50.0
    )
    oil = Item(
        code="RM-OIL",
        name="Refined Palmolein Cooking Oil",
        category=ItemCategory.RAW_MATERIAL,
        unit="litres",
        standard_cost=110.0,
        current_wauc=110.0,
        reorder_level=10.0
    )
    pouch = Item(
        code="PK-POUCH-200G",
        name="Printed Snack Foil Pouch 200g",
        category=ItemCategory.PACKAGING,
        unit="pieces",
        standard_cost=1.50,
        current_wauc=1.50,
        reorder_level=200.0
    )
    carton = Item(
        code="PK-CARTON-20PK",
        name="Corrugated Master Shipper Carton (20 pk)",
        category=ItemCategory.PACKAGING,
        unit="cartons",
        standard_cost=25.00,
        current_wauc=25.00,
        reorder_level=15.0
    )
    finished_good = Item(
        code="FG-SNACK-200G",
        name="Crunchy Sev Bhujia 200g",
        category=ItemCategory.FINISHED_GOOD,
        unit="packets",
        standard_cost=18.50,
        current_wauc=18.50,
        reorder_level=100.0
    )
    db.add_all([flour, oil, pouch, carton, finished_good])
    db.flush()

    # 5. Bill of Materials (BOM)
    # Standard batch size: 1 standard batch produces 250 packets
    bom = BOM(
        finished_good_id=finished_good.id,
        code="BOM-SNACK-200G-V1",
        name="Standard Recipe - Crunchy Bhujia 200g",
        batch_size=1.0,
        yield_packets=250.0,
        pack_carton_capacity=20,
        is_active=True
    )
    db.add(bom)
    db.flush()

    bom_lines = [
        BOMLine(bom_id=bom.id, item_id=flour.id, standard_quantity=40.0, unit="kg"),
        BOMLine(bom_id=bom.id, item_id=oil.id, standard_quantity=5.0, unit="litres"),
        BOMLine(bom_id=bom.id, item_id=pouch.id, standard_quantity=250.0, unit="pieces"),
        BOMLine(bom_id=bom.id, item_id=carton.id, standard_quantity=12.5, unit="cartons"),
    ]
    db.add_all(bom_lines)
    db.commit()

    # 6. Step 1: Initial Stock Injection via Ledger
    # Record starting stock via append-only ledger moves
    inventory_service.record_stock_move(
        item_id=flour.id,
        move_type=StockMoveType.STOCK_ADJUSTMENT,
        direction=StockMoveDirection.IN,
        quantity=100.0,
        unit="kg",
        unit_cost=40.0,
        reference_type="initial_stock",
        reference_id="INIT-001",
        notes="Opening inventory"
    )
    inventory_service.record_stock_move(
        item_id=oil.id,
        move_type=StockMoveType.STOCK_ADJUSTMENT,
        direction=StockMoveDirection.IN,
        quantity=25.0,
        unit="litres",
        unit_cost=110.0,
        reference_type="initial_stock",
        reference_id="INIT-001",
        notes="Opening inventory"
    )
    inventory_service.record_stock_move(
        item_id=pouch.id,
        move_type=StockMoveType.STOCK_ADJUSTMENT,
        direction=StockMoveDirection.IN,
        quantity=550.0,
        unit="pieces",
        unit_cost=1.50,
        reference_type="initial_stock",
        reference_id="INIT-001",
        notes="Opening inventory"
    )
    inventory_service.record_stock_move(
        item_id=carton.id,
        move_type=StockMoveType.STOCK_ADJUSTMENT,
        direction=StockMoveDirection.IN,
        quantity=32.0,
        unit="cartons",
        unit_cost=25.00,
        reference_type="initial_stock",
        reference_id="INIT-001",
        notes="Opening inventory"
    )
    db.commit()

    # 7. Step 2: Milestone Purchase Transaction: 60 kg flour at ₹45/kg
    purchase_service.record_purchase(
        invoice_no="INV-NIT-FLOUR-60",
        supplier_id=supplier_flour.id,
        lines_data=[
            {
                "item_id": flour.id,
                "quantity": 60.0,
                "unit": "kg",
                "unit_price": 45.0
            }
        ],
        notes="Benchmark purchase: 60 kg flour @ ₹45/kg"
    )

    # 8. Step 3: Milestone Production Run
    # Run consumes:
    # - 40 kg flour (Standard 40kg)
    # - 5.5 litres oil (Standard 5.0L -> Usage variance +0.5L)
    # - 244 pouches (238 good + 6 damaged)
    # - 11 cartons (available/used for packing)
    # Output:
    # - 238 Good Packets (Expected 250 -> Yield loss 12 packets)
    # - Damaged packets: 6
    # Packaging Reconciliation:
    # - 11 cartons * 20 capacity = 220 capacity
    # - Good packets = 238
    # - Unboxed packets = 18
    # - Packaging mismatch warning triggered!
    production_service.record_production_run(
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
            {"category": "labour", "description": "Fryer operator and packaging staff", "amount": 650.0},
            {"category": "power", "description": "Electric fryer & sealing machine", "amount": 220.0},
            {"category": "gas", "description": "Commercial LPG heating", "amount": 380.0}
        ],
        notes="NIT Benchmark Production Run"
    )

    # Compute final balances
    balances = {item.code: inventory_service.get_stock_balance(item.id) for item in [flour, oil, pouch, carton, finished_good]}
    print("Seeding complete. Current Stock Balances:")
    for code, bal in balances.items():
        print(f"  {code}: {bal}")
    return balances


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
