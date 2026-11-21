"""
Production API endpoints for YieldTrace.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ProductionRun, BOM, User, UserRole
from app.modules.production.service import ProductionService
from app.modules.costing.service import CostingService
from app.modules.auth.service import require_roles

router = APIRouter(prefix="/api/production", tags=["Production"])


class ActualConsumptionInput(BaseModel):
    item_id: int
    actual_quantity: float = Field(gt=0)
    unit: Optional[str] = None


class OverheadInput(BaseModel):
    category: str
    description: Optional[str] = None
    amount: float = Field(ge=0)


class ProductionRunCreateRequest(BaseModel):
    run_number: str
    bom_id: int
    planned_batches: float = Field(gt=0, default=1.0)
    actual_consumptions: List[ActualConsumptionInput]
    good_packets_produced: float = Field(ge=0)
    damaged_packets: float = Field(ge=0, default=0.0)
    cartons_used: float = Field(ge=0, default=0.0)
    carton_capacity: Optional[int] = None
    overheads: Optional[List[OverheadInput]] = None
    notes: Optional[str] = None


@router.get("/boms")
def list_boms(db: Session = Depends(get_db)):
    """
    List all active BOM recipes and requirements.
    """
    boms = db.query(BOM).filter(BOM.is_active == True).all()
    return [
        {
            "id": b.id,
            "code": b.code,
            "name": b.name,
            "finished_good": b.finished_good.name if b.finished_good else None,
            "batch_size": b.batch_size,
            "yield_packets": b.yield_packets,
            "pack_carton_capacity": b.pack_carton_capacity,
            "lines": [
                {
                    "item_id": line.item_id,
                    "item_name": line.item.name,
                    "standard_quantity": line.standard_quantity,
                    "unit": line.unit,
                    "standard_cost": line.item.standard_cost
                }
                for line in b.lines
            ]
        }
        for b in boms
    ]


@router.post("/runs")
def record_production_run(
    payload: ProductionRunCreateRequest,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.PRODUCTION_SUPERVISOR])),
    db: Session = Depends(get_db)
):
    """
    Record and execute a production run with:
    - Usage variance calculation
    - Packaging reconciliation with mandatory audit warning
    - Append-only stock movements
    Restricted to Owner, Admin, and Production Supervisor.
    """
    service = ProductionService(db)
    try:
        consumptions = [c.model_dump() for c in payload.actual_consumptions]
        overheads = [oh.model_dump() for oh in payload.overheads] if payload.overheads else None

        run = service.record_production_run(
            run_number=payload.run_number,
            bom_id=payload.bom_id,
            planned_batches=payload.planned_batches,
            actual_consumptions=consumptions,
            good_packets_produced=payload.good_packets_produced,
            damaged_packets=payload.damaged_packets,
            cartons_used=payload.cartons_used,
            carton_capacity=payload.carton_capacity,
            overheads_data=overheads,
            notes=payload.notes
        )

        return {
            "id": run.id,
            "run_number": run.run_number,
            "status": run.status.value,
            "good_packets_produced": run.output.actual_good_packets if run.output else 0,
            "cartons_used": run.output.cartons_used if run.output else 0,
            "unboxed_packets": run.output.unboxed_packets if run.output else 0,
            "packaging_mismatch": run.output.packaging_mismatch if run.output else False,
            "audit_warning": run.output.audit_warning if run.output else None,
            "message": "Production run recorded successfully."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runs/{run_id}/costing")
def get_run_costing(run_id: int, db: Session = Depends(get_db)):
    """
    Variance forensics and cost waterfall breakdown for a production run.
    """
    service = CostingService(db)
    try:
        return service.calculate_cost_waterfall(run_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
