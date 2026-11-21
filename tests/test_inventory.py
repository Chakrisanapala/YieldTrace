"""
Unit tests for Inventory Service and Append-Only Stock Ledger.
"""
import pytest
from app.models import Item, ItemCategory, StockMove, StockMoveType, StockMoveDirection
from app.modules.inventory.service import InventoryService


def test_append_only_ledger_balance_calculation(db_session):
    """
    Critical Rule: Stock balances are NEVER updated directly.
    They must be calculated strictly by summing append-only movements.
    """
    item = Item(
        code="RM-TEST",
        name="Test Raw Material",
        category=ItemCategory.RAW_MATERIAL,
        unit="kg",
        standard_cost=50.0,
        current_wauc=50.0
    )
    db_session.add(item)
    db_session.commit()

    service = InventoryService(db_session)

    # Initial balance should be 0
    assert service.get_stock_balance(item.id) == 0.0

    # 1. First purchase IN: 100 kg
    move1 = service.record_stock_move(
        item_id=item.id,
        move_type=StockMoveType.PURCHASE_RECEIPT,
        direction=StockMoveDirection.IN,
        quantity=100.0,
        unit="kg",
        unit_cost=50.0,
        reference_type="purchase",
        reference_id="PO-001"
    )
    assert move1.balance_after == 100.0
    assert service.get_stock_balance(item.id) == 100.0

    # 2. Production issue OUT: 35 kg
    move2 = service.record_stock_move(
        item_id=item.id,
        move_type=StockMoveType.PRODUCTION_ISSUE,
        direction=StockMoveDirection.OUT,
        quantity=35.0,
        unit="kg",
        unit_cost=50.0,
        reference_type="production_run",
        reference_id="RUN-001"
    )
    assert move2.balance_after == 65.0
    assert service.get_stock_balance(item.id) == 65.0

    # Verify ledger history length
    moves = db_session.query(StockMove).filter(StockMove.item_id == item.id).all()
    assert len(moves) == 2


def test_weighted_average_cost_update(db_session):
    """
    Verify Weighted-Average Unit Cost (WAUC) formula:
    WAUC_new = (Current_Qty * Current_WAUC + Added_Qty * Added_Price) / Total_Qty
    """
    item = Item(
        code="RM-FLOUR",
        name="Flour",
        category=ItemCategory.RAW_MATERIAL,
        unit="kg",
        standard_cost=40.0,
        current_wauc=40.0
    )
    db_session.add(item)
    db_session.commit()

    service = InventoryService(db_session)

    # Starting with 100 kg @ ₹40
    service.record_stock_move(
        item.id, StockMoveType.STOCK_ADJUSTMENT, StockMoveDirection.IN, 100.0, "kg", 40.0, "init", "001"
    )

    # New purchase: 60 kg @ ₹45/kg
    # Expected WAUC = (100 * 40 + 60 * 45) / 160 = (4000 + 2700) / 160 = 6700 / 160 = 41.875
    new_wauc = service.update_weighted_average_cost(item.id, 60.0, 45.0)
    assert new_wauc == 41.875
    assert item.current_wauc == 41.875
