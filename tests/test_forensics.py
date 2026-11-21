"""
Unit tests for Variance Forensics Engine, Statistical Baselines, and CUSUM Drift.
"""
import pytest
from app.models import Item, ProductionRun, RunConsumption, RunOutput
from app.modules.insight.forensics_service import VarianceForensicsService


def test_sample_size_fallback_logic(db_session):
    """
    Forensics baseline rule:
    N < 10: Flags is_reliable=False, uses 3% fallback.
    N >= 10: Flags is_reliable=True, calculates mean, std_dev, median, mad.
    """
    item = Item(code="RM-TEST-STAT", name="Stat Item", category="raw_material", unit="kg", standard_cost=50.0, current_wauc=50.0)
    db_session.add(item)
    db_session.commit()

    service = VarianceForensicsService(db_session)

    # 1. Test with 3 observations (< 10)
    for i in [1.5, 2.0, -1.0]:
        rc = RunConsumption(run_id=1, item_id=item.id, planned_quantity=10, actual_quantity=10, unit="kg", variance_percentage=i)
        db_session.add(rc)
    db_session.commit()

    b_low = service.compute_material_baseline(item.id)
    assert b_low["sample_count"] == 3
    assert b_low["is_reliable"] is False
    assert b_low["fallback_tolerance_percent"] == 3.0
    assert "Baseline not yet reliable" in b_low["status_note"]

    # 2. Add 8 more observations -> Total 11 (>= 10)
    for i in [0.5, -0.5, 1.0, 0.0, 1.2, -1.2, 0.8, -0.8]:
        rc = RunConsumption(run_id=1, item_id=item.id, planned_quantity=10, actual_quantity=10, unit="kg", variance_percentage=i)
        db_session.add(rc)
    db_session.commit()

    b_high = service.compute_material_baseline(item.id)
    assert b_high["sample_count"] == 11
    assert b_high["is_reliable"] is True
    assert "mean" in b_high
    assert "std_dev" in b_high
    assert "median" in b_high
    assert "mad" in b_high


def test_cusum_drift_detection(db_session):
    """Test CUSUM sequential drift calculation on an injected drift series."""
    item = Item(code="RM-CUSUM", name="CUSUM Item", category="raw_material", unit="kg", standard_cost=10.0, current_wauc=10.0)
    db_session.add(item)
    db_session.commit()

    # Create 10 sequential runs with upward drift after run 6
    variances = [0.1, -0.1, 0.2, 0.0, 0.3, 2.5, 3.8, 4.2, 5.0, 5.5]
    for idx, v in enumerate(variances, 1):
        r = ProductionRun(run_number=f"RUN-DRIFT-{idx}", bom_id=1, planned_batches=1.0, supervisor="Test", is_synthetic=True)
        db_session.add(r)
        db_session.flush()
        rc = RunConsumption(run_id=r.id, item_id=item.id, planned_quantity=10, actual_quantity=10, unit="kg", variance_percentage=v)
        db_session.add(rc)
    db_session.commit()

    service = VarianceForensicsService(db_session)
    res = service.detect_cusum_drift(item.id, target_mean=0.0, allowable_shift_k=1.0, decision_threshold_h=3.0)
    assert res["drift_detected"] is True
    assert len(res["cusum_series"]) == 10
