"""
SQLAlchemy ORM Models for YieldTrace.

Complete enterprise schema for:
- Users & Role-Based Access Control (Owner, Admin, Salesman, Production Supervisor, Accountant, Auditor)
- Product & Item Master (Raw Materials, Packaging, Finished Goods) with GST and standard costs
- Unit Conversions
- Suppliers and Customers (with GSTIN, State, Contact details)
- Bill of Materials (BOM & BOMLines) with versioning
- Procurement (Purchases, PurchaseLines, Idempotency)
- Append-Only Stock Movements Ledger (stock_moves)
- Production Runs (RunConsumption, RunOutput, Overheads, Synthetic Flag)
- Sales Orders, OrderLines, Allocations, Dispatches, Backorders
- GST Invoices & InvoiceLines (CGST, SGST, IGST intra/inter-state)
- Payments & Customer Receivables
- Production Variance Forensics Findings & Historical Baselines
- Immutable System Audit Logs
"""
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, Numeric, Boolean, DateTime,
    ForeignKey, Text, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.orm import relationship
from app.database import Base


# ==========================================
# Enumerations
# ==========================================
class UserRole(str, PyEnum):
    OWNER = "owner"
    ADMIN = "admin"
    SALESMAN = "salesman"
    PRODUCTION_SUPERVISOR = "production_supervisor"
    ACCOUNTANT = "accountant"
    AUDITOR = "auditor"


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
    STOCK_REVERSAL = "STOCK_REVERSAL"


class ProductionRunStatus(str, PyEnum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class OrderStatus(str, PyEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    FULFILLED = "FULFILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class InvoiceStatus(str, PyEnum):
    ISSUED = "ISSUED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


# ==========================================
# 1. Users and Authentication
# ==========================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    password_salt = Column(String(64), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.PRODUCTION_SUPERVISOR, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    session_token = Column(String(128), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = Column(DateTime, nullable=True)


# ==========================================
# 2. Items Master
# ==========================================
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False, index=True)
    category = Column(SQLEnum(ItemCategory), nullable=False, index=True)
    unit = Column(String(20), nullable=False)  # kg, litres, pieces, cartons, packets
    standard_cost = Column(Float, default=0.0, nullable=False)  # Reference standard BOM price
    current_wauc = Column(Float, default=0.0, nullable=False)   # Weighted-Average Unit Cost
    selling_price = Column(Float, default=0.0, nullable=False)  # Selling price for finished goods
    gst_rate = Column(Float, default=5.0, nullable=False)       # Default GST rate in %
    reorder_level = Column(Float, default=0.0, nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

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
    multiplier = Column(Float, nullable=False)  # from_unit * multiplier = to_unit
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True)


# ==========================================
# 4. Customers and Suppliers
# ==========================================
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False, index=True)
    gstin = Column(String(20), nullable=True, index=True)
    state = Column(String(50), default="Tamil Nadu", nullable=False)
    contact_phone = Column(String(50), nullable=True)
    contact_email = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    purchases = relationship("Purchase", back_populates="supplier")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False, index=True)
    customer_type = Column(String(50), default="retailer")  # retailer / distributor
    gstin = Column(String(20), nullable=True, index=True)
    state = Column(String(50), default="Tamil Nadu", nullable=False)
    contact_phone = Column(String(50), nullable=True)
    contact_email = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    orders = relationship("SalesOrder", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")
    payments = relationship("Payment", back_populates="customer")


# ==========================================
# 5. Bill of Materials (BOM) & BOM Lines
# ==========================================
class BOM(Base):
    __tablename__ = "bom"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    finished_good_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    version = Column(String(20), default="1.0", nullable=False)
    batch_size = Column(Float, default=1.0, nullable=False)
    yield_packets = Column(Float, nullable=False)            # e.g., standard 200 packets for Murukku 200g
    pack_carton_capacity = Column(Integer, default=20, nullable=False)  # 20 packets per carton
    standard_overhead = Column(Float, default=1800.0, nullable=False)   # ₹1,800 standard batch overhead
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    finished_good = relationship("Item", back_populates="bom_recipes")
    lines = relationship("BOMLine", back_populates="bom", cascade="all, delete-orphan")
    runs = relationship("ProductionRun", back_populates="bom")


class BOMLine(Base):
    __tablename__ = "bom_lines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bom_id = Column(Integer, ForeignKey("bom.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    standard_quantity = Column(Float, nullable=False)  # Standard qty required for 1 standard batch
    unit = Column(String(20), nullable=False)
    scrap_allowance_percent = Column(Float, default=0.0)

    bom = relationship("BOM", back_populates="lines")
    item = relationship("Item")


# ==========================================
# 6. Procurement & Purchase Transactions
# ==========================================
class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_no = Column(String(100), unique=True, nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    purchase_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    total_amount = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="RECEIVED", nullable=False)
    idempotency_token = Column(String(100), unique=True, nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

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
    batch_reference = Column(String(50), nullable=True)
    bom_id = Column(Integer, ForeignKey("bom.id"), nullable=False)
    bom_version = Column(String(20), default="1.0", nullable=False)
    planned_batches = Column(Float, default=1.0, nullable=False)
    status = Column(SQLEnum(ProductionRunStatus), default=ProductionRunStatus.COMPLETED, nullable=False)
    supervisor = Column(String(100), default="Supervisor Lead", nullable=False)
    is_synthetic = Column(Boolean, default=False, nullable=False, index=True)  # Clear tag for demo history
    start_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    end_time = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    bom = relationship("BOM", back_populates="runs")
    consumptions = relationship("RunConsumption", back_populates="run", cascade="all, delete-orphan")
    output = relationship("RunOutput", back_populates="run", uselist=False, cascade="all, delete-orphan")
    overheads = relationship("Overhead", back_populates="run", cascade="all, delete-orphan")
    variance_findings = relationship("VarianceFinding", back_populates="run", cascade="all, delete-orphan")


class RunConsumption(Base):
    __tablename__ = "run_consumption"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("production_runs.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    planned_quantity = Column(Float, nullable=False)
    actual_quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    standard_unit_cost = Column(Float, default=0.0, nullable=False)
    actual_unit_cost = Column(Float, default=0.0, nullable=False)  # Weighted average cost at issue
    usage_variance_qty = Column(Float, default=0.0, nullable=False)   # actual_qty - planned_qty
    usage_variance_cost = Column(Float, default=0.0, nullable=False)  # (actual - planned) * standard_cost
    variance_percentage = Column(Float, default=0.0, nullable=False) # ((actual - planned) / planned) * 100

    run = relationship("ProductionRun", back_populates="consumptions")
    item = relationship("Item")


class RunOutput(Base):
    __tablename__ = "run_output"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("production_runs.id"), nullable=False, index=True)
    finished_good_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    planned_good_packets = Column(Float, nullable=False)
    actual_good_packets = Column(Float, nullable=False)
    damaged_packets = Column(Float, default=0.0, nullable=False)
    damaged_pouches = Column(Float, default=0.0, nullable=False)  # Exact damaged pouches recorded independently
    unboxed_packets = Column(Float, default=0.0, nullable=False)
    cartons_used = Column(Float, default=0.0, nullable=False)
    carton_capacity = Column(Integer, default=20, nullable=False)
    packaging_mismatch = Column(Boolean, default=False, nullable=False)
    audit_warning = Column(String(255), nullable=True)
    yield_percentage = Column(Float, default=0.0, nullable=False)       # actual / planned * 100
    yield_variance_percentage = Column(Float, default=0.0, nullable=False) # (actual - planned) / planned * 100
    yield_variance_packets = Column(Float, default=0.0, nullable=False) # actual - planned
    yield_variance_cost = Column(Float, default=0.0, nullable=False)

    run = relationship("ProductionRun", back_populates="output")
    finished_good = relationship("Item")


# ==========================================
# 8. Append-Only Stock Movements Ledger
# ==========================================
class StockMove(Base):
    """
    CRITICAL ARCHITECTURAL RULE:
    Stock balances are NEVER directly updated or overwritten.
    Balances are derived from the append-only stock_moves ledger.
    Every balance query calculates SUM(IN) - SUM(OUT).
    """
    __tablename__ = "stock_moves"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    move_type = Column(SQLEnum(StockMoveType), nullable=False, index=True)
    direction = Column(SQLEnum(StockMoveDirection), nullable=False, index=True)  # IN or OUT
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    unit_cost = Column(Float, default=0.0, nullable=False)
    total_cost = Column(Float, default=0.0, nullable=False)
    reference_type = Column(String(50), nullable=False, index=True)  # purchase, production_run, dispatch, adjustment
    reference_id = Column(String(100), nullable=False, index=True)   # invoice_no, run_number, order_id, etc.
    notes = Column(String(255), nullable=True)
    balance_after = Column(Float, nullable=False)        # Audit snapshot after movement
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    item = relationship("Item", back_populates="stock_moves")


# ==========================================
# 9. Overheads Allocation
# ==========================================
class Overhead(Base):
    __tablename__ = "overheads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("production_runs.id"), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # labour, gas_electricity, power, maintenance
    description = Column(String(255), nullable=True)
    amount = Column(Float, nullable=False)
    allocation_method = Column(String(50), default="direct_batch", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    run = relationship("ProductionRun", back_populates="overheads")


# ==========================================
# 10. Sales Orders & Order Lines
# ==========================================
class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    order_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.DRAFT, nullable=False, index=True)
    total_ordered_qty = Column(Float, default=0.0, nullable=False)
    total_fulfilled_qty = Column(Float, default=0.0, nullable=False)
    total_backordered_qty = Column(Float, default=0.0, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    customer = relationship("Customer", back_populates="orders")
    lines = relationship("SalesOrderLine", back_populates="order", cascade="all, delete-orphan")
    dispatches = relationship("Dispatch", back_populates="order", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="order")


class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    ordered_quantity = Column(Float, nullable=False)
    fulfilled_quantity = Column(Float, default=0.0, nullable=False)
    backordered_quantity = Column(Float, default=0.0, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    order = relationship("SalesOrder", back_populates="lines")
    item = relationship("Item")


# ==========================================
# 11. Dispatches
# ==========================================
class Dispatch(Base):
    __tablename__ = "dispatches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    dispatch_number = Column(String(50), unique=True, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    dispatched_quantity = Column(Float, nullable=False)
    dispatch_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    order = relationship("SalesOrder", back_populates="dispatches")
    item = relationship("Item")


# ==========================================
# 12. GST Invoices & Invoice Lines
# ==========================================
class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_no = Column(String(50), unique=True, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    invoice_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_interstate = Column(Boolean, default=False, nullable=False)
    taxable_amount = Column(Float, default=0.0, nullable=False)
    cgst_amount = Column(Float, default=0.0, nullable=False)
    sgst_amount = Column(Float, default=0.0, nullable=False)
    igst_amount = Column(Float, default=0.0, nullable=False)
    total_amount = Column(Float, default=0.0, nullable=False)
    paid_amount = Column(Float, default=0.0, nullable=False)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.ISSUED, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    customer = relationship("Customer", back_populates="invoices")
    order = relationship("SalesOrder", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice")


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    taxable_amount = Column(Float, nullable=False)
    gst_rate = Column(Float, default=5.0, nullable=False)
    cgst_amount = Column(Float, default=0.0, nullable=False)
    sgst_amount = Column(Float, default=0.0, nullable=False)
    igst_amount = Column(Float, default=0.0, nullable=False)
    total_amount = Column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="lines")
    item = relationship("Item")


# ==========================================
# 13. Payments & Customer Outstanding
# ==========================================
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    receipt_no = Column(String(50), unique=True, nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    payment_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    amount = Column(Float, nullable=False)
    payment_mode = Column(String(50), default="BANK_TRANSFER", nullable=False)  # CASH, CHEQUE, UPI, BANK_TRANSFER
    reference_no = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    invoice = relationship("Invoice", back_populates="payments")
    customer = relationship("Customer", back_populates="payments")


# ==========================================
# 14. Variance Forensics Findings
# ==========================================
class VarianceFinding(Base):
    """
    Persisted explainable decision-support findings from the Forensics Engine.
    Answers the 9 core questions:
    1. Expected 2. Actual 3. Deviation point 4. Deviation size 5. Historical context
    6. Supporting evidence 7. Supervisor investigation recommendation 8. Financial impact 9. Source trace
    """
    __tablename__ = "variance_findings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("production_runs.id"), nullable=False, index=True)
    finding_title = Column(String(150), nullable=False)
    severity = Column(String(20), default="WARNING", nullable=False)  # INFO, WARNING, CRITICAL
    affected_material = Column(String(100), nullable=False)
    expected_value = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=False)
    difference = Column(Float, nullable=False)
    difference_percentage = Column(Float, nullable=False)
    historical_baseline_mean = Column(Float, nullable=True)
    historical_baseline_range = Column(String(100), nullable=True)
    sample_size = Column(Integer, default=0, nullable=False)
    detection_method = Column(String(100), nullable=False)  # FIXED_TOLERANCE_FALLBACK, HISTORICAL_IQR, CUSUM_DRIFT
    confidence_limitations = Column(Text, nullable=True)
    financial_impact = Column(Float, default=0.0, nullable=False)
    recommended_investigation = Column(Text, nullable=False)
    source_transaction_ref = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    run = relationship("ProductionRun", back_populates="variance_findings")


# ==========================================
# 15. Historical Baselines
# ==========================================
class HistoricalBaseline(Base):
    __tablename__ = "historical_baselines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False)  # usage_variance_percent, yield_percent
    sample_count = Column(Integer, default=0, nullable=False)
    mean = Column(Float, default=0.0, nullable=False)
    std_dev = Column(Float, default=0.0, nullable=False)
    median = Column(Float, default=0.0, nullable=False)
    mad = Column(Float, default=0.0, nullable=False)  # Median Absolute Deviation
    is_reliable = Column(Boolean, default=False, nullable=False)  # True only if sample_count >= 10
    calculated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    item = relationship("Item")


# ==========================================
# 16. Audit Logs
# ==========================================
class AuditLog(Base):
    """
    Immutable system audit trail. Every operational event, warning,
    and stock adjustment is logged permanently.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    table_name = Column(String(50), nullable=False, index=True)
    record_id = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DISPATCH, AUDIT_WARNING, ADJUSTMENT
    changed_by = Column(String(50), default="system", nullable=False)
    old_values = Column(Text, nullable=True)
    new_values = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
