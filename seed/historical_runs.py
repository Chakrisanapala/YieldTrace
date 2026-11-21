"""
Historical production runs seed data for YieldTrace.
Generates multi-day production history to power variance forensics and CUSUM analysis.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import Item, BOM
from app.modules.production.service import ProductionService


def seed_historical_runs(db: Session, num_runs: int = 10):
    bom = db.query(BOM).filter(BOM.is_active == True).first()
    if not bom:
        print("No active BOM found. Run seed_data.py first.")
        return

    flour = db.query(Item).filter(Item.code == "RM-FLOUR").first()
    oil = db.query(Item).filter(Item.code == "RM-OIL").first()
    pouch = db.query(Item).filter(Item.code == "PK-POUCH-200G").first()
    carton = db.query(Item).filter(Item.code == "PK-CARTON-20PK").first()

    prod_service = ProductionService(db)

    # Base date 10 days ago
    start_date = datetime.now(timezone.utc) - timedelta(days=num_runs)

    # Simulated historical variance data
    history = [
        {"flour": 40.2, "oil": 5.1, "pouches": 248, "cartons": 12, "good": 240, "damaged": 8},
        {"flour": 39.8, "oil": 4.9, "pouches": 252, "cartons": 12, "good": 246, "damaged": 6},
        {"flour": 41.0, "oil": 5.3, "pouches": 250, "cartons": 12, "good": 242, "damaged": 8},
        {"flour": 40.0, "oil": 5.0, "pouches": 249, "cartons": 12, "good": 245, "damaged": 4},
        {"flour": 42.5, "oil": 5.6, "pouches": 255, "cartons": 11, "good": 235, "damaged": 15},
    ]

    print(f"Adding {len(history)} historical production runs...")
    for idx, run_data in enumerate(history, 1):
        run_no = f"RUN-HIST-{idx:03d}"
        try:
            prod_service.record_production_run(
                run_number=run_no,
                bom_id=bom.id,
                planned_batches=1.0,
                actual_consumptions=[
                    {"item_id": flour.id, "actual_quantity": run_data["flour"], "unit": "kg"},
                    {"item_id": oil.id, "actual_quantity": run_data["oil"], "unit": "litres"},
                    {"item_id": pouch.id, "actual_quantity": run_data["pouches"], "unit": "pieces"},
                    {"item_id": carton.id, "actual_quantity": run_data["cartons"], "unit": "cartons"},
                ],
                good_packets_produced=run_data["good"],
                damaged_packets=run_data["damaged"],
                cartons_used=run_data["cartons"],
                carton_capacity=20,
                overheads_data=[
                    {"category": "labour", "amount": 600.0},
                    {"category": "power", "amount": 200.0},
                    {"category": "gas", "amount": 350.0}
                ],
                notes=f"Historical run {idx}"
            )
        except Exception as e:
            print(f"Skipping run {run_no}: {e}")
