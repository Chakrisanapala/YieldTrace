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
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import (
    User, UserRole, Item, ItemCategory,
    Supplier, Customer, BOM, BOMLine, UnitConversion,
    StockMoveType, StockMoveDirection
)
from app.modules.inventory.service import InventoryService

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory database session for each test."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def seeded_benchmark_db(db_session):
    """Fixture providing the initial state before benchmark purchase and run."""
    # 1. Users
    user = User(username="admin", email="admin@yieldtrace.local", hashed_password="pass", role=UserRole.ADMIN)
    db_session.add(user)

    # 2. Supplier
    supplier = Supplier(name="Annapurna Agro Mills", code="SUP-FLOUR-01")
    db_session.add(supplier)

    # 3. Items
    flour = Item(
        code="RM-FLOUR",
        name="Refined Wheat Flour",
        category=ItemCategory.RAW_MATERIAL,
        unit="kg",
        standard_cost=40.0,
        current_wauc=40.0
    )
    oil = Item(
        code="RM-OIL",
        name="Cooking Oil",
        category=ItemCategory.RAW_MATERIAL,
        unit="litres",
        standard_cost=110.0,
        current_wauc=110.0
    )
    pouch = Item(
        code="PK-POUCH-200G",
        name="Snack Pouch 200g",
        category=ItemCategory.PACKAGING,
        unit="pieces",
        standard_cost=1.50,
        current_wauc=1.50
    )
    carton = Item(
        code="PK-CARTON-20PK",
        name="Master Carton",
        category=ItemCategory.PACKAGING,
        unit="cartons",
        standard_cost=25.00,
        current_wauc=25.00
    )
    finished_good = Item(
        code="FG-SNACK-200G",
        name="Sev Bhujia 200g",
        category=ItemCategory.FINISHED_GOOD,
        unit="packets",
        standard_cost=18.50,
        current_wauc=18.50
    )
    db_session.add_all([flour, oil, pouch, carton, finished_good])
    db_session.flush()

    # 4. BOM
    bom = BOM(
        finished_good_id=finished_good.id,
        code="BOM-SNACK-200G",
        name="Standard Snack Recipe",
        batch_size=1.0,
        yield_packets=250.0,
        pack_carton_capacity=20,
        is_active=True
    )
    db_session.add(bom)
    db_session.flush()

    bom_lines = [
        BOMLine(bom_id=bom.id, item_id=flour.id, standard_quantity=40.0, unit="kg"),
        BOMLine(bom_id=bom.id, item_id=oil.id, standard_quantity=5.0, unit="litres"),
        BOMLine(bom_id=bom.id, item_id=pouch.id, standard_quantity=250.0, unit="pieces"),
        BOMLine(bom_id=bom.id, item_id=carton.id, standard_quantity=12.5, unit="cartons"),
    ]
    db_session.add_all(bom_lines)
    db_session.flush()

    # 5. Opening Stock Movements
    inv = InventoryService(db_session)
    inv.record_stock_move(flour.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 100.0, "kg", 40.0, "initial", "INIT")
    inv.record_stock_move(oil.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 25.0, "litres", 110.0, "initial", "INIT")
    inv.record_stock_move(pouch.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 550.0, "pieces", 1.5, "initial", "INIT")
    inv.record_stock_move(carton.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 32.0, "cartons", 25.0, "initial", "INIT")

    db_session.commit()
    return db_session
