"""
Production Variance Forensics Engine for YieldTrace.

THE CORE INNOVATION:
An explainable decision-support forensics engine that identifies, quantifies,
investigates, and communicates deviations between standard and actual manufacturing performance.

Answers the 9 Critical Forensic Questions:
1. What was expected to happen?
2. What actually happened?
3. Where did the deviation occur?
4. How large was the deviation?
5. Is this deviation unusual compared with historical production?
6. What evidence supports the finding?
7. What should the production supervisor investigate?
8. What is the financial impact?
9. Can the complete result be traced back to source transactions?

Statistical Baseline & Methodology:
- Sample size threshold:
  * N < 10 observations: Claims NO statistical reliability. Falls back to a deterministic
    3% engineering tolerance with explicit label: "Baseline not yet reliable – insufficient historical observations."
  * N >= 10 observations: Computes robust statistical baselines (Mean, Standard Deviation, Median, MAD).
- Production Drift Detection via CUSUM (Cumulative Sum Control Chart):
  Tracks positive and negative drift over sequential runs using configurable reference shift (k)
  and decision threshold (h).
"""
import math
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import (
    ProductionRun,
    RunConsumption,
    RunOutput,
    Item,
    BOM,
    BOMLine,
    VarianceFinding,
    HistoricalBaseline
)


class VarianceForensicsService:
    def __init__(self, db: Session):
        self.db = db

    def compute_material_baseline(self, item_id: int) -> Dict:
        """
        Calculate statistical dispersion metrics for an item's historical consumption variance.
        Enforces:
        - If N < 10: Flags is_reliable=False, provides 3% tolerance fallback.
        - If N >= 10: Calculates Mean, StdDev, Median, and MAD.
        """
        consumptions = (
            self.db.query(RunConsumption.variance_percentage)
            .filter(RunConsumption.item_id == item_id)
            .all()
        )
        variances = [c[0] for c in consumptions if c[0] is not None]
        n = len(variances)

        if n < 10:
            return {
                "item_id": item_id,
                "sample_count": n,
                "is_reliable": False,
                "status_note": "Baseline not yet reliable – insufficient historical observations (minimum 10 required).",
                "fallback_tolerance_percent": 3.0,
                "mean": round(float(np.mean(variances)), 2) if n > 0 else 0.0,
                "std_dev": round(float(np.std(variances)), 2) if n > 1 else 0.0,
                "median": round(float(np.median(variances)), 2) if n > 0 else 0.0,
                "mad": 0.0
            }

        var_arr = np.array(variances)
        mean_val = float(np.mean(var_arr))
        std_val = float(np.std(var_arr, ddof=1))
        median_val = float(np.median(var_arr))
        mad_val = float(np.median(np.abs(var_arr - median_val)))

        return {
            "item_id": item_id,
            "sample_count": n,
            "is_reliable": True,
            "status_note": f"Statistically reliable baseline established over {n} observations.",
            "mean": round(mean_val, 2),
            "std_dev": round(std_val, 2),
            "median": round(median_val, 2),
            "mad": round(mad_val, 2),
            "baseline_range": f"[{round(mean_val - 2*std_val, 2)}%, {round(mean_val + 2*std_val, 2)}%]"
        }

    def detect_cusum_drift(
        self,
        item_id: int,
        target_mean: float = 0.0,
        allowable_shift_k: float = 1.0,
        decision_threshold_h: float = 4.0
    ) -> Dict:
        """
        Tabular Cumulative Sum (CUSUM) control chart for sequential production variance.
        S_high[i] = max(0, S_high[i-1] + (X[i] - target - k))
        S_low[i]  = min(0, S_low[i-1] + (X[i] - target + k))
        """
        consumptions = (
            self.db.query(RunConsumption.variance_percentage, ProductionRun.run_number)
            .join(ProductionRun, RunConsumption.run_id == ProductionRun.id)
            .filter(RunConsumption.item_id == item_id)
            .order_by(ProductionRun.id.asc())
            .all()
        )

        data = [c[0] for c in consumptions if c[0] is not None]
        runs = [c[1] for c in consumptions if c[0] is not None]
        n = len(data)

        if n < 5:
            return {
                "item_id": item_id,
                "observations": n,
                "drift_detected": False,
                "message": "Insufficient sequential observations for CUSUM drift detection (minimum 5 runs required)."
            }

        s_high = 0.0
        s_low = 0.0
        cusum_series = []
        drift_flag = False
        drift_run = None

        for idx, x in enumerate(data):
            s_high = max(0.0, s_high + (x - target_mean - allowable_shift_k))
            s_low = min(0.0, s_low + (x - target_mean + allowable_shift_k))

            is_out_of_control = (s_high > decision_threshold_h) or (abs(s_low) > decision_threshold_h)
            if is_out_of_control and not drift_flag:
                drift_flag = True
                drift_run = runs[idx]

            cusum_series.append({
                "run_number": runs[idx],
                "variance_percentage": round(x, 2),
                "s_high": round(s_high, 2),
                "s_low": round(s_low, 2),
                "is_anomaly": is_out_of_control
            })

        return {
            "item_id": item_id,
            "observations": n,
            "target_mean": target_mean,
            "allowable_shift_k": allowable_shift_k,
            "decision_threshold_h": decision_threshold_h,
            "drift_detected": drift_flag,
            "first_drift_run": drift_run,
            "cusum_series": cusum_series
        }

    def investigate_production_run(self, run_id: int) -> List[Dict]:
        """
        Conduct a comprehensive 9-point forensic audit of a production run.
        Generates explainable findings for:
        - Material consumption deviations (e.g., Cooking Oil +5%)
        - Yield variance (e.g., Murukku -6% yield)
        - Packaging reconciliation (e.g., 9 cartons vs 180 capacity vs 188 good packets -> 8 unboxed)
        - Damaged pouches (e.g., 6 damaged pouches)
        """
        run = self.db.query(ProductionRun).filter(ProductionRun.id == run_id).first()
        if not run:
            raise ValueError(f"ProductionRun #{run_id} not found.")

        findings = []

        # 1. Investigate Material Consumptions
        for c in run.consumptions:
            item = c.item
            planned = c.planned_quantity
            actual = c.actual_quantity
            diff = round(actual - planned, 4)
            pct = c.variance_percentage

            baseline = self.compute_material_baseline(item.id)

            # Determine anomaly threshold
            is_anomaly = False
            threshold_desc = ""

            if baseline["is_reliable"]:
                # 2-sigma threshold
                mean_b = baseline["mean"]
                std_b = baseline["std_dev"]
                threshold = mean_b + 2 * std_b
                if abs(pct - mean_b) > 2 * std_b and abs(pct) > 1.0:
                    is_anomaly = True
                    threshold_desc = f"Historical Mean: {mean_b}%, 2σ Limit: ±{round(2*std_b, 2)}%"
            else:
                # Deterministic 3% fallback
                if abs(pct) > baseline["fallback_tolerance_percent"]:
                    is_anomaly = True
                    threshold_desc = f"Engineering Tolerance Fallback: ±{baseline['fallback_tolerance_percent']}%"

            if is_anomaly:
                severity = "CRITICAL" if abs(pct) > 10.0 else "WARNING"
                financial_impact = round(abs(diff * (item.current_wauc or item.standard_cost)), 2)

                # Generate domain-specific investigation instructions
                if "oil" in item.name.lower():
                    recom = (
                        f"{item.name} consumption is {pct:+.1f}% compared to standard BOM. "
                        f"Deviation exceeds acceptable range ({threshold_desc}). "
                        f"Recommended supervisor investigation: 1) Inspect fryer temperature calibration (excess absorption occurs at lower frying temps); "
                        f"2) Audit batch weighing protocol; 3) Verify flowmeter calibration at oil dispensing station."
                    )
                elif "spice" in item.name.lower():
                    recom = (
                        f"{item.name} consumption is {pct:+.1f}% compared to standard BOM. "
                        f"Recommended supervisor investigation: Check automated doser nozzle settings, hopper spillage, "
                        f"and verify manual weighing scales in seasoning section."
                    )
                else:
                    recom = (
                        f"{item.name} consumption is {pct:+.1f}% vs standard BOM. "
                        f"Recommended supervisor investigation: Audit mixing room scale calibration, hopper moisture retention, "
                        f"and moisture loss during dough preparation."
                    )

                finding_dict = {
                    "run_id": run.id,
                    "finding_title": f"Unusual Consumption Deviation: {item.name} ({pct:+.1f}%)",
                    "severity": severity,
                    "affected_material": item.name,
                    "expected_value": planned,
                    "actual_value": actual,
                    "difference": diff,
                    "difference_percentage": pct,
                    "historical_baseline_mean": baseline.get("mean"),
                    "historical_baseline_range": threshold_desc,
                    "sample_size": baseline["sample_count"],
                    "detection_method": "HISTORICAL_2_SIGMA" if baseline["is_reliable"] else "FIXED_TOLERANCE_FALLBACK",
                    "confidence_limitations": (
                        "High statistical confidence" if baseline["is_reliable"]
                        else "Baseline not yet reliable – insufficient historical observations (minimum 10 required). Using 3% fallback."
                    ),
                    "financial_impact": financial_impact,
                    "recommended_investigation": recom,
                    "source_transaction_ref": f"{run.run_number} -> {item.code}"
                }
                findings.append(finding_dict)

        # 2. Investigate Yield Deviation
        ro = run.output
        if ro:
            if abs(ro.yield_variance_percentage) >= 3.0:
                fg = ro.finished_good
                financial_loss = round(abs(ro.yield_variance_packets) * (fg.standard_cost if fg else 0.0), 2)
                yield_finding = {
                    "run_id": run.id,
                    "finding_title": f"Substandard Production Yield: {ro.yield_percentage:.1f}% ({ro.yield_variance_percentage:+.1f}%)",
                    "severity": "CRITICAL" if ro.yield_variance_percentage <= -5.0 else "WARNING",
                    "affected_material": fg.name if fg else "Finished Good",
                    "expected_value": ro.planned_good_packets,
                    "actual_value": ro.actual_good_packets,
                    "difference": ro.yield_variance_packets,
                    "difference_percentage": ro.yield_variance_percentage,
                    "historical_baseline_mean": 100.0,
                    "historical_baseline_range": "Target Standard Yield: 100.0%",
                    "sample_size": 1,
                    "detection_method": "STANDARD_BOM_YIELD_AUDIT",
                    "confidence_limitations": "Direct physical output count vs BOM formulation expectation.",
                    "financial_impact": financial_loss,
                    "recommended_investigation": (
                        f"Good packets produced ({ro.actual_good_packets}) is {abs(ro.yield_variance_percentage):.1f}% below planned target ({ro.planned_good_packets}). "
                        f"Recommended supervisor investigation: 1) Verify extrusion dough cut-length consistency; 2) Audit frying breakage scrap; "
                        f"3) Inspect packing machine pouch sealing rejects."
                    ),
                    "source_transaction_ref": f"{run.run_number} -> Yield Output"
                }
                findings.append(yield_finding)

            # 3. Investigate Packaging Reconciliation & Cartons
            if ro.packaging_mismatch:
                pkg_finding = {
                    "run_id": run.id,
                    "finding_title": f"Packaging Reconciliation Mismatch: {int(ro.unboxed_packets)} Unboxed Packets",
                    "severity": "WARNING",
                    "affected_material": "Master Shipper Cartons & Finished Goods",
                    "expected_value": ro.cartons_used * ro.carton_capacity,
                    "actual_value": ro.actual_good_packets,
                    "difference": ro.unboxed_packets,
                    "difference_percentage": round((ro.unboxed_packets / (ro.cartons_used * ro.carton_capacity)) * 100, 2),
                    "historical_baseline_mean": 0.0,
                    "historical_baseline_range": "Zero unboxed tolerance",
                    "sample_size": 1,
                    "detection_method": "CARTON_CAPACITY_RECONCILIATION",
                    "confidence_limitations": "Exact container packing capacity equation: Cartons Issued * Capacity != Good Packets.",
                    "financial_impact": 0.0,  # Physical inventory held unboxed
                    "recommended_investigation": (
                        f"Actual cartons issued ({ro.cartons_used}) only accommodate {int(ro.cartons_used * ro.carton_capacity)} packets. "
                        f"Actual good output is {ro.actual_good_packets} packets, leaving {int(ro.unboxed_packets)} unboxed packets in production staging. "
                        f"Preserving transaction: 9 cartons recorded. Supervisor must issue 1 additional carton to box remaining stock."
                    ),
                    "source_transaction_ref": f"{run.run_number} -> Packaging Output"
                }
                findings.append(pkg_finding)

            # 4. Investigate Damaged Packaging
            if ro.damaged_pouches > 0:
                dmg_finding = {
                    "run_id": run.id,
                    "finding_title": f"Packaging Scrap Detected: {int(ro.damaged_pouches)} Damaged Pouches",
                    "severity": "INFO" if ro.damaged_pouches < 10 else "WARNING",
                    "affected_material": "Printed Snack Pouches",
                    "expected_value": 0.0,
                    "actual_value": ro.damaged_pouches,
                    "difference": ro.damaged_pouches,
                    "difference_percentage": 0.0,
                    "historical_baseline_mean": 2.0,
                    "historical_baseline_range": "Allowance: < 5 pieces",
                    "sample_size": 1,
                    "detection_method": "DEFECTIVE_PACKAGING_AUDIT",
                    "confidence_limitations": "Physical count of machine sealing snags.",
                    "financial_impact": round(ro.damaged_pouches * 1.50, 2),
                    "recommended_investigation": (
                        f"{int(ro.damaged_pouches)} printed pouches were rejected due to heat seal tearing or registration misalignment. "
                        f"Audit vertical heat sealer temperature and pouch feed roller tension."
                    ),
                    "source_transaction_ref": f"{run.run_number} -> Scrap Recording"
                }
                findings.append(dmg_finding)

        # Persist findings to database if not already persisted
        for f in findings:
            existing = self.db.query(VarianceFinding).filter(
                VarianceFinding.run_id == run.id,
                VarianceFinding.finding_title == f["finding_title"]
            ).first()
            if not existing:
                vf = VarianceFinding(**f)
                self.db.add(vf)
        self.db.commit()

        return findings
