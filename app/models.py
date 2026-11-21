"""
SQLAlchemy ORM models for YieldTrace.
Includes all core Day 1 entities:
- users
- items
- unit_conversions
- customers
- suppliers
- bom & bom_lines
- purchases & purchase_lines
- production_runs
- run_consumption
- run_output
- stock_moves (append-only ledger)
- overheads
- audit_logs
"""
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(str, PyEnum):
    ADMIN = "admin"
    PRODUCTION = "production"
    AUDITOR = "auditor"
    SALESMAN = "salesman"


class ItemCategory(str, PyEnum):
    RAW_MATERIAL = "raw_material"
    PACKAGING = "packaging"
    FINISHED_GOOD = "finished_good"


class StockMoveDirection(str, PyEnum):
    IN = "IN"
    OUT = "OUT"


class StockMoveType(str, PyEnum):
    PURCHASE_RECEIPT = "PURCHASE_RECEIPT"
    PRODUCTION_ISSUE = "PRODUCTION_ISSUE"
    PRODUCTION_RECEIPT = "PRODUCTION_RECEIPT"
    PRODUCTION_SCRAP = "PRODUCTION_SCRAP"
    PACKAGING_CONSUMPTION = "PACKAGING_CONSUMPTION"
    SALES_DISPATCH = "SALES_DISPATCH"
    STOCK_ADJUSTMENT = "STOCK_ADJUSTMENT"


class ProductionRunStatus(str, PyEnum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ==========================================
# 1. Users
# ==========================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.PRODUCTION, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ==========================================
# 2. Items Master
# ==========================================
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    category = Column(SQLEnum(ItemCategory), nullable=False, index=True)
    unit = Column(String(20), nullable=False)  # kg, litres, pieces, cartons
    standard_cost = Column(Float, default=0.0, nullable=False)  # Reference BOM price
    current_wauc = Column(Float, default=0.0, nullable=False)   # Weighted-average unit cost
    reorder_level = Column(Float, default=0.0)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    stock_moves = relationship("StockMove", back_populates="item")
    bom_recipes = relationship("BOM", back_populates="finished_good")


# ==========================================
# 3. Unit Conversions
# ==========================================
class UnitConversion(Base):
    __tablename__ = "unit_conversions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    from_unit = Column(String(20), nullable=False, index=True)
    to_unit = Column(String(20), nullable=False, index=True)
    multiplier = Column(Float, nullable=False)  # e.g., 1 kg = 1000 g (multiplier=1000)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True)  # optional item-specific conversion


# ==========================================
# 4. Customers and Suppliers
# ==========================================
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False)
    contact_phone = Column(String(50), nullable=True)
    contact_email = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    purchases = relationship("Purchase", back_populates="supplier")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False)
    customer_type = Column(String(50), default="retailer")  # retailer / distributor
    contact_phone = Column(String(50), nullable=True)
    contact_email = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ==========================================
# 5. Bill of Materials (BOM) & BOM Lines
# ==========================================
class BOM(Base):
    __tablename__ = "bom"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    finished_good_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    batch_size = Column(Float, default=1.0, nullable=False)  # e.g., 1 batch or 100 units
    yield_packets = Column(Float, nullable=False)            # standard output packets per batch
    pack_carton_capacity = Column(Integer, default=20)       # e.g. 20 packets per carton
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    finished_good = relationship("Item", back_populates="bom_recipes")
    lines = relationship("BOMLine", back_populates="bom", cascade="all, delete-orphan")
    runs = relationship("ProductionRun", back_populates="bom")


class BOMLine(Base):
    __tablename__ = "bom_lines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bom_id = Column(Integer, ForeignKey("bom.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    standard_quantity = Column(Float, nullable=False)  # quantity required for 1 standard batch
    unit = Column(String(20), nullable=False)
    scrap_allowance_percent = Column(Float, default=0.0)

    bom = relationship("BOM", back_populates="lines")
    item = relationship("Item")


# ==========================================
# 6. Purchases & Purchase Lines
# ==========================================
class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_no = Column(String(100), unique=True, nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    purchase_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_amount = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="RECEIVED")  # RECEIVED, PENDING, CANCELLED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    supplier = relationship("Supplier", back_populates="purchases")
    lines = relationship("PurchaseLine", back_populates="purchase", cascade="all, delete-orphan")


class PurchaseLine(Base):
    __tablename__ = "purchase_lines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    price_variance = Column(Float, default=0.0)  # (actual price - standard price) * quantity

    purchase = relationship("Purchase", back_populates="lines")
    item = relationship("Item")


# ==========================================
# 7. Production Runs, Consumption & Output
# ==========================================
class ProductionRun(Base):
    __tablename__ = "production_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_number = Column(String(50), unique=True, nullable=False, index=True)
    bom_id = Column(Integer, ForeignKey("bom.id"), nullable=False)
    planned_batches = Column(Float, default=1.0, nullable=False)
    status = Column(SQLEnum(ProductionRunStatus), default=ProductionRunStatus.COMPLETED)
    start_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    bom = relationship("BOM", back_populates="runs")
    consumptions = relationship("RunConsumption", back_populates="run", cascade="all, delete-orphan")
    output = relationship("RunOutput", back_populates="run", uselist=False, cascade="all, delete-orphan")
    overheads = relationship("Overhead", back_populates="run", cascade="all, delete-orphan")


class RunConsumption(Base):
    __tablename__ = "run_consumption"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("production_runs.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    planned_quantity = Column(Float, nullable=False)
    actual_quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    standard_unit_cost = Column(Float, default=0.0)
    actual_unit_cost = Column(Float, default=0.0)  # WAUC at time of consumption
    usage_variance_qty = Column(Float, default=0.0)  # actual_quantity - planned_quantity
    usage_variance_cost = Column(Float, default=0.0) # (actual - planned) * standard_cost

    run = relationship("ProductionRun", back_populates="consumptions")
    item = relationship("Item")


class RunOutput(Base):
    __tablename__ = "run_output"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("production_runs.id"), nullable=False, index=True)
    finished_good_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    planned_good_packets = Column(Float, nullable=False)
    actual_good_packets = Column(Float, nullable=False)
    damaged_packets = Column(Float, default=0.0)
    unboxed_packets = Column(Float, default=0.0)
    cartons_used = Column(Float, default=0.0)
    carton_capacity = Column(Integer, default=20)
    packaging_mismatch = Column(Boolean, default=False)
    audit_warning = Column(String(255), nullable=True)
    yield_variance_packets = Column(Float, default=0.0)  # planned - actual
    yield_variance_cost = Column(Float, default=0.0)

    run = relationship("ProductionRun", back_populates="output")
    finished_good = relationship("Item")


# ==========================================
# 8. Append-Only Stock Movements Ledger
# ==========================================
class StockMove(Base):
    """
    CRITICAL DATABASE RULE:
    Stock balances are NEVER directly updated or overwritten.
    Balances are derived from the append-only stock_moves ledger.
    """
    __tablename__ = "stock_moves"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    move_type = Column(SQLEnum(StockMoveType), nullable=False, index=True)
    direction = Column(SQLEnum(StockMoveDirection), nullable=False)  # IN or OUT
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    unit_cost = Column(Float, default=0.0, nullable=False)
    total_cost = Column(Float, default=0.0, nullable=False)
    reference_type = Column(String(50), nullable=False)  # purchase, production_run, adjustment, sales
    reference_id = Column(String(100), nullable=False)   # invoice_no, run_number, etc.
    notes = Column(String(255), nullable=True)
    balance_after = Column(Float, nullable=False)        # Running calculated balance snapshot
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    item = relationship("Item", back_populates="stock_moves")


# ==========================================
# 9. Overheads Allocation
# ==========================================
class Overhead(Base):
    __tablename__ = "overheads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("production_runs.id"), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # labour, power, gas, machine_depreciation
    description = Column(String(255), nullable=True)
    amount = Column(Float, nullable=False)
    allocation_method = Column(String(50), default="direct_run")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    run = relationship("ProductionRun", back_populates="overheads")


# ==========================================
# 10. Audit Logs
# ==========================================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    table_name = Column(String(50), nullable=False, index=True)
    record_id = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, AUDIT_WARNING
    changed_by = Column(String(50), default="system")
    old_values = Column(Text, nullable=True)
    new_values = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
