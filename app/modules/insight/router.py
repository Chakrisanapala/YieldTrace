"""
Variance Forensics and Production Planning API endpoints for YieldTrace.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.modules.insight.forensics_service import VarianceForensicsService
from app.modules.insight.planner_service import ProductionPlannerService

router = APIRouter(prefix="/api/insight", tags=["Variance Forensics & Planning"])


@router.get("/forensics/run/{run_id}")
def get_run_forensic_investigation(run_id: int, db: Session = Depends(get_db)):
    """
    Get explainable forensic findings for a specific production run.
    Answers the 9 critical questions with evidence, root-cause recommendations, and financial impact.
    """
    service = VarianceForensicsService(db)
    try:
        findings = service.investigate_production_run(run_id)
        return {
            "run_id": run_id,
            "findings_count": len(findings),
            "findings": findings
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/forensics/baseline/{item_id}")
def get_material_baseline(item_id: int, db: Session = Depends(get_db)):
    """
    Get statistical baseline for an item (Mean, StdDev, Median, MAD).
    Shows sample size and whether 3% fallback is active.
    """
    service = VarianceForensicsService(db)
    try:
        return service.compute_material_baseline(item_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/forensics/cusum/{item_id}")
def get_cusum_drift(
    item_id: int,
    target: float = Query(0.0),
    k: float = Query(1.0),
    h: float = Query(4.0),
    db: Session = Depends(get_db)
):
    """
    Calculate Tabular CUSUM drift detection for an item's variance series over time.
    """
    service = VarianceForensicsService(db)
    try:
        return service.detect_cusum_drift(item_id, target, k, h)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/planner/evaluate")
def evaluate_production_plan(
    finished_good_id: int = Query(...),
    target_demand: Optional[float] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Deterministic production feasibility & shortage analysis.
    Checks live stock of finished goods and raw materials for required batches.
    """
    service = ProductionPlannerService(db)
    try:
        return service.plan_production_for_demand(finished_good_id, target_demand)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
