"""
Historical Production Runs Seed Script for YieldTrace.
Generates 40 reproducible synthetic runs for Variance Forensics and CUSUM Drift Analysis.

Guards:
- Fixed random seed: np.random.seed(42) for exact reproducibility.
- Clear audit tag: is_synthetic = True on every synthetic run record.
- Does NOT alter the canonical NIT benchmark run or closing balances of the benchmark run.
- Populates historical_baselines table when N >= 10.
"""
from datetime import datetime, timedelta, timezone
import numpy as np
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Item, BOM, BOMLine, ProductionRun, RunConsumption, RunOutput, Overhead, HistoricalBaseline
from app.modules.insight.forensics_service import VarianceForensicsService


def seed_synthetic_history(db: Session, num_runs: int = 40):
    """Generate 40 reproducible historical production runs tagged is_synthetic=True."""
    np.random.seed(42)

    bom = db.query(BOM).filter(BOM.is_active == True).first()
    if not bom:
        print("No active BOM found. Run seed_data.py first.")
        return

    flour = db.query(Item).filter(Item.code == "RM-FLOUR").first()
    oil = db.query(Item).filter(Item.code == "RM-OIL").first()
    spice_mix = db.query(Item).filter(Item.code == "RM-SPICE-MIX").first()
    pouches = db.query(Item).filter(Item.code == "PK-POUCH-200G").first()
    cartons = db.query(Item).filter(Item.code == "PK-CARTON-20PK").first()
    fg = bom.finished_good

    # Remove previous synthetic runs to maintain clean idempotent state
    prev_synthetic = db.query(ProductionRun).filter(ProductionRun.is_synthetic == True).all()
    for ps in prev_synthetic:
        db.delete(ps)
    db.commit()

    base_date = datetime.now(timezone.utc) - timedelta(days=num_runs + 5)

    print(f"Generating {num_runs} reproducible synthetic runs (Seed=42, is_synthetic=True)...")

    # Generate normal distributions with slight simulated process drift around run 25
    for i in range(1, num_runs + 1):
        run_date = base_date + timedelta(days=i)
        run_no = f"RUN-SYNTH-{i:03d}"

        # Standard BOM baseline for 1 batch = 200 packets
        # Injected drift after run 28: Oil consumption increases by +4% on average (e.g. fryer thermostat wearing out)
        oil_drift = 0.4 if i > 28 else 0.0

        flour_actual = round(float(np.random.normal(40.1, 0.3)), 2)
        oil_actual = round(float(np.random.normal(10.0 + oil_drift, 0.25)), 2)
        spice_actual = round(float(np.random.normal(1.01, 0.04)), 2)
        good_packets = int(np.random.normal(197, 2.5))
        damaged_pouches = int(np.random.choice([1, 2, 3, 4], p=[0.4, 0.3, 0.2, 0.1]))
        total_pouches = good_packets + damaged_pouches
        cartons_used = int(np.ceil(good_packets / 20.0))

        run = ProductionRun(
            run_number=run_no,
            batch_reference=f"BATCH-SYNTH-{i:03d}",
            bom_id=bom.id,
            bom_version=bom.version,
            planned_batches=1.0,
            supervisor="Automated Synthetic History",
            is_synthetic=True,
            start_time=run_date,
            end_time=run_date + timedelta(hours=3),
            notes=f"Synthetic historical demonstration run #{i}",
            created_at=run_date
        )
        db.add(run)
        db.flush()

        # Consumptions
        items_cons = [
            (flour, 40.0, flour_actual),
            (oil, 10.0, oil_actual),
            (spice_mix, 1.0, spice_actual),
            (pouches, 200.0, float(total_pouches)),
            (cartons, 10.0, float(cartons_used)),
        ]

        for item, planned_q, actual_q in items_cons:
            diff_q = round(actual_q - planned_q, 4)
            pct = round((diff_q / planned_q) * 100, 2)
            rc = RunConsumption(
                run_id=run.id,
                item_id=item.id,
                planned_quantity=planned_q,
                actual_quantity=actual_q,
                unit=item.unit,
                standard_unit_cost=item.standard_cost,
                actual_unit_cost=item.standard_cost,
                usage_variance_qty=diff_q,
                usage_variance_cost=round(diff_q * item.standard_cost, 2),
                variance_percentage=pct
            )
            db.add(rc)

        # Output
        yield_pct = round((good_packets / 200.0) * 100, 2)
        yield_var_pct = round(((good_packets - 200.0) / 200.0) * 100, 2)
        boxed_capacity = cartons_used * 20
        mismatch = (good_packets != boxed_capacity)
        unboxed = max(0, good_packets - boxed_capacity)

        ro = RunOutput(
            run_id=run.id,
            finished_good_id=fg.id,
            planned_good_packets=200.0,
            actual_good_packets=float(good_packets),
            damaged_packets=float(damaged_pouches),
            damaged_pouches=float(damaged_pouches),
            unboxed_packets=float(unboxed),
            cartons_used=float(cartons_used),
            carton_capacity=20,
            packaging_mismatch=mismatch,
            audit_warning=f"Unboxed: {unboxed}" if mismatch else None,
            yield_percentage=yield_pct,
            yield_variance_percentage=yield_var_pct,
            yield_variance_packets=float(good_packets - 200),
            yield_variance_cost=round(max(0, 200 - good_packets) * fg.standard_cost, 2)
        )
        db.add(ro)

        # Overhead
        db.add(Overhead(run_id=run.id, category="labour", description="Direct labour", amount=1200.0))
        db.add(Overhead(run_id=run.id, category="gas_electricity", description="Gas & electricity", amount=600.0))

    db.commit()

    # Recompute and persist Historical Baselines for all raw materials
    forensics = VarianceForensicsService(db)
    print("Computing statistical baselines across all historical runs...")
    for item in [flour, oil, spice_mix, pouches, cartons]:
        b = forensics.compute_material_baseline(item.id)
        if b["is_reliable"]:
            hb = HistoricalBaseline(
                item_id=item.id,
                metric_type="usage_variance_percent",
                sample_count=b["sample_count"],
                mean=b["mean"],
                std_dev=b["std_dev"],
                median=b["median"],
                mad=b["mad"],
                is_reliable=True,
                calculated_at=datetime.now(timezone.utc)
            )
            db.add(hb)
    db.commit()
    print("Historical baseline computation completed.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_synthetic_history(db, num_runs=40)
    finally:
        db.close()
