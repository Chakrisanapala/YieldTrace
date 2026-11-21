"""
Unit tests for Inventory Service and Append-Only Stock Ledger.
"""
import pytest
from app.models import Item, ItemCategory, StockMove, StockMoveType, StockMoveDirection
from app.modules.inventory.service import InventoryService, InsufficientStockError


def test_append_only_ledger_invariance(db_session):
    """Stock balances are strictly derived from SUM(IN) - SUM(OUT)."""
    item = Item(code="RM-TEST", name="Test Material", category=ItemCategory.RAW_MATERIAL, unit="kg", standard_cost=50.0, current_wauc=50.0)
    db_session.add(item)
    db_session.commit()

    inv = InventoryService(db_session)
    assert inv.get_stock_balance(item.id) == 0.0

    # Receipt IN: 100 kg
    inv.record_stock_move(item.id, StockMoveType.PURCHASE_RECEIPT, StockMoveDirection.IN, 100.0, "kg", 50.0, "purchase", "P-1")
    assert inv.get_stock_balance(item.id) == 100.0

    # Issue OUT: 40 kg
    inv.record_stock_move(item.id, StockMoveType.PRODUCTION_ISSUE, StockMoveDirection.OUT, 40.0, "kg", 50.0, "prod", "RUN-1")
    assert inv.get_stock_balance(item.id) == 60.0

    # Verify ledger history length
    moves = db_session.query(StockMove).filter(StockMove.item_id == item.id).all()
    assert len(moves) == 2


def test_prevention_of_negative_inventory(db_session):
    """System must raise InsufficientStockError when issue exceeds available stock."""
    item = Item(code="RM-FLOUR-TEST", name="Flour Test", category=ItemCategory.RAW_MATERIAL, unit="kg", standard_cost=40.0, current_wauc=40.0)
    db_session.add(item)
    db_session.commit()

    inv = InventoryService(db_session)
    inv.record_stock_move(item.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 20.0, "kg", 40.0, "init", "001")

    # Attempting to issue 25 kg when only 20 kg is available must fail
    with pytest.raises(InsufficientStockError) as exc_info:
        inv.record_stock_move(item.id, StockMoveType.PRODUCTION_ISSUE, StockMoveDirection.OUT, 25.0, "kg", 40.0, "prod", "RUN-ERR")
    assert "Insufficient stock" in str(exc_info.value)

    # Balance must remain unchanged at 20.0
    assert inv.get_stock_balance(item.id) == 20.0


def test_auditable_stock_adjustments(db_session):
    """Adjustments must create signed movement without overwriting historical records."""
    item = Item(code="RM-ADJ", name="Adj Item", category=ItemCategory.RAW_MATERIAL, unit="kg", standard_cost=100.0, current_wauc=100.0)
    db_session.add(item)
    db_session.commit()

    inv = InventoryService(db_session)
    inv.record_stock_move(item.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 50.0, "kg", 100.0, "init", "001")

    # Auditor adjusts physical stock to 48.0 kg (2.0 kg shrinkage)
    move = inv.record_stock_adjustment(item.id, 48.0, reason="Annual physical stock count shrinkage", adjusted_by="auditor_lead")
    assert move.direction == StockMoveDirection.OUT
    assert move.quantity == 2.0
    assert inv.get_stock_balance(item.id) == 48.0
