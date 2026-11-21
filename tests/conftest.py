"""
Pytest configuration and test database fixtures for YieldTrace.
"""
import sys
from pathlib import Path

# Ensure root directory is on pythonpath
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.database import Base
import app.models
from app.models import (
    User, UserRole, Item, ItemCategory,
    Supplier, Customer, BOM, BOMLine, UnitConversion,
    StockMoveType, StockMoveDirection
)
from app.modules.auth.service import AuthService
from app.modules.inventory.service import InventoryService

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory database session for each test."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def canonical_benchmark_setup(db_session):
    """
    Fixture providing the canonical NIT benchmark initial state.
    Product: Murukku 200 g
    Initial stock:
    - Flour: 100 kg @ ₹40/kg
    - Cooking oil: 30 litres @ ₹110/L
    - Spice mix: 5 kg @ ₹250/kg
    - Printed pouches: 500 pieces @ ₹1.50
    - Cartons: 30 cartons @ ₹25.00
    - Finished Murukku 200 g: 50 packets @ ₹20.00
    """
    auth = AuthService(db_session)
    inv = InventoryService(db_session)

    # 1. Users
    auth.register_user("admin", "admin@yieldtrace.local", "Password@123", UserRole.ADMIN, "System Admin")
    auth.register_user("sales", "sales@yieldtrace.local", "Password@123", UserRole.SALESMAN, "Sales Rep")
    auth.register_user("prod", "prod@yieldtrace.local", "Password@123", UserRole.PRODUCTION_SUPERVISOR, "Prod Lead")
    auth.register_user("auditor", "auditor@yieldtrace.local", "Password@123", UserRole.AUDITOR, "Auditor Lead")

    # 2. Suppliers & Customers
    sup = Supplier(code="SUP-FLOUR-01", name="Annapurna Agro Mills", gstin="33AAAAA0000A1Z5", state="Tamil Nadu")
    ret_a = Customer(code="CUST-RET-A", name="Retailer A", customer_type="retailer", gstin="33DDDDD3333D4Z8", state="Tamil Nadu")
    dist_b = Customer(code="CUST-DIST-B", name="Distributor B", customer_type="distributor", gstin="29EEEEE4444E5Z9", state="Karnataka")
    db_session.add_all([sup, ret_a, dist_b])
    db_session.flush()

    # 3. Item Master
    flour = Item(code="RM-FLOUR", name="Flour", category=ItemCategory.RAW_MATERIAL, unit="kg", standard_cost=40.0, current_wauc=40.0)
    oil = Item(code="RM-OIL", name="Cooking oil", category=ItemCategory.RAW_MATERIAL, unit="litres", standard_cost=110.0, current_wauc=110.0)
    spice = Item(code="RM-SPICE-MIX", name="Spice mix", category=ItemCategory.RAW_MATERIAL, unit="kg", standard_cost=250.0, current_wauc=250.0)
    pouches = Item(code="PK-POUCH-200G", name="Printed pouches", category=ItemCategory.PACKAGING, unit="pieces", standard_cost=1.50, current_wauc=1.50)
    cartons = Item(code="PK-CARTON-20PK", name="Cartons", category=ItemCategory.PACKAGING, unit="cartons", standard_cost=25.00, current_wauc=25.00)
    murukku = Item(code="FG-MURUKKU-200G", name="Murukku 200 g", category=ItemCategory.FINISHED_GOOD, unit="packets", standard_cost=20.0, current_wauc=20.0, selling_price=50.0, gst_rate=5.0)

    db_session.add_all([flour, oil, spice, pouches, cartons, murukku])
    db_session.flush()

    # 4. Standard BOM: Murukku 200g (200 packets per batch)
    bom = BOM(
        finished_good_id=murukku.id,
        code="BOM-MURUKKU-200G-V1",
        name="Standard Murukku 200g Recipe",
        version="1.0",
        batch_size=1.0,
        yield_packets=200.0,
        pack_carton_capacity=20,
        standard_overhead=1800.0,
        is_active=True
    )
    db_session.add(bom)
    db_session.flush()

    bom_lines = [
        BOMLine(bom_id=bom.id, item_id=flour.id, standard_quantity=40.0, unit="kg"),
        BOMLine(bom_id=bom.id, item_id=oil.id, standard_quantity=10.0, unit="litres"),
        BOMLine(bom_id=bom.id, item_id=spice.id, standard_quantity=1.0, unit="kg"),
        BOMLine(bom_id=bom.id, item_id=pouches.id, standard_quantity=200.0, unit="pieces"),
        BOMLine(bom_id=bom.id, item_id=cartons.id, standard_quantity=10.0, unit="cartons"),
    ]
    db_session.add_all(bom_lines)
    db_session.flush()

    # 5. Opening Stock Movements
    inv.record_stock_move(flour.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 100.0, "kg", 40.0, "initial", "INIT")
    inv.record_stock_move(oil.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 30.0, "litres", 110.0, "initial", "INIT")
    inv.record_stock_move(spice.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 5.0, "kg", 250.0, "initial", "INIT")
    inv.record_stock_move(pouches.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 500.0, "pieces", 1.50, "initial", "INIT")
    inv.record_stock_move(cartons.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 30.0, "cartons", 25.00, "initial", "INIT")
    inv.record_stock_move(murukku.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 50.0, "packets", 20.00, "initial", "INIT")

    db_session.commit()
    return db_session
