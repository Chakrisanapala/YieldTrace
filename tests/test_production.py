"""
Unit tests for Production Service, BOM standards, and packaging reconciliation.
"""
import pytest
from app.models import Item, BOM, ProductionRun
from app.modules.production.service import ProductionService


def test_packaging_reconciliation_warning(canonical_benchmark_setup):
    """
    Validates packaging reconciliation:
    Cartons issued: 9 (capacity 20 -> 180 packets).
    Good packets produced: 188.
    Unboxed packets: 8.
    Preserves actual transaction and flags discrepancy without silent modification.
    """
    db = canonical_benchmark_setup
    prod = ProductionService(db)

    bom = db.query(BOM).first()
    flour = db.query(Item).filter(Item.code == "RM-FLOUR").first()
    oil = db.query(Item).filter(Item.code == "RM-OIL").first()
    spice = db.query(Item).filter(Item.code == "RM-SPICE-MIX").first()
    pouches = db.query(Item).filter(Item.code == "PK-POUCH-200G").first()
    cartons = db.query(Item).filter(Item.code == "PK-CARTON-20PK").first()

    run = prod.record_production_run(
        run_number="RUN-PKG-RECON-01",
        bom_id=bom.id,
        planned_batches=1.0,
        actual_consumptions=[
            {"item_id": flour.id, "actual_quantity": 40.0, "unit": "kg"},
            {"item_id": oil.id, "actual_quantity": 10.5, "unit": "litres"},
            {"item_id": spice.id, "actual_quantity": 1.2, "unit": "kg"},
            {"item_id": pouches.id, "actual_quantity": 194.0, "unit": "pieces"},
            {"item_id": cartons.id, "actual_quantity": 9.0, "unit": "cartons"},
        ],
        good_packets_produced=188.0,
        damaged_packets=6.0,
        damaged_pouches=6.0,
        cartons_used=9.0,
        carton_capacity=20,
        notes="Reconciliation run"
    )

    ro = run.output
    assert ro.actual_good_packets == 188.0
    assert ro.cartons_used == 9.0
    assert ro.carton_capacity == 20
    assert ro.unboxed_packets == 8.0
    assert ro.packaging_mismatch is True
    assert "Unboxed packets: 8" in ro.audit_warning
