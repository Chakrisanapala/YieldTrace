"""
Unit tests for Production Service, BOM standards, and packaging reconciliation.
"""
import pytest
from app.models import Item, BOM, BOMLine, ProductionRun
from app.modules.production.service import ProductionService


def test_packaging_reconciliation_warning_example(seeded_benchmark_db):
    """
    Test the prompt's exact packaging reconciliation scenario:
    Good packets produced: 188
    Cartons available for packing: 9
    Carton capacity: 180 packets (9 * 20)
    Unboxed packets: 8
    Audit warning - packaging mismatch
    The system must preserve actual transaction and flag discrepancy without silent coercion.
    """
    db = seeded_benchmark_db
    prod_service = ProductionService(db)

    bom = db.query(BOM).first()
    flour = db.query(Item).filter(Item.code == "RM-FLOUR").first()
    oil = db.query(Item).filter(Item.code == "RM-OIL").first()
    pouch = db.query(Item).filter(Item.code == "PK-POUCH-200G").first()
    carton = db.query(Item).filter(Item.code == "PK-CARTON-20PK").first()

    run = prod_service.record_production_run(
        run_number="RUN-RECON-188",
        bom_id=bom.id,
        planned_batches=1.0,
        actual_consumptions=[
            {"item_id": flour.id, "actual_quantity": 30.0, "unit": "kg"},
            {"item_id": oil.id, "actual_quantity": 4.0, "unit": "litres"},
            {"item_id": pouch.id, "actual_quantity": 190.0, "unit": "pieces"},
            {"item_id": carton.id, "actual_quantity": 9.0, "unit": "cartons"},
        ],
        good_packets_produced=188.0,
        damaged_packets=2.0,
        cartons_used=9.0,
        carton_capacity=20,
        notes="Reconciliation example run"
    )

    output = run.output
    assert output is not None
    assert output.actual_good_packets == 188.0
    assert output.cartons_used == 9.0
    assert output.carton_capacity == 20
    assert output.unboxed_packets == 8.0
    assert output.packaging_mismatch is True
    assert "Audit warning – packaging mismatch" in output.audit_warning
    assert "Unboxed packets: 8" in output.audit_warning
