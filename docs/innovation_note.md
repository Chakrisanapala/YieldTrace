# Research & Innovation Note: Production Variance Forensics

**Subject:** Explainable Decision-Support Intelligence in Small-Scale Food Manufacturing  
**Author:** YieldTrace Engineering Team  
**Institution:** National Institute of Technology Tiruchirappalli (NIT Trichy), Centre for Digital Infrastructure  
**Internship:** Winter Internship 2026  

---

## Abstract
Small food manufacturing operations operate under tight gross margins (often 12–18%) and face chronic profitability erosion caused by unexplained variations between recipe formulation (Bill of Materials) and actual factory execution. Existing Enterprise Resource Planning (ERP) systems treat manufacturing as static bookkeeping, providing aggregate monthly summaries that obscure the exact physical station where losses occurred.

We introduce **Production Variance Forensics**, an explainable, ledger-grounded decision-support architecture. Rather than relying on uninterpretable deep-learning black boxes, the engine synthesizes standard absorption costing, immutable double-entry material balance invariants, and Tabular Cumulative Sum (CUSUM) statistical process control. It answers nine critical diagnostic questions for every batch execution, providing plant supervisors with actionable root-cause hypotheses while guaranteeing exact mathematical cost waterfall reconciliation down to the paisa.

---

## 1. Introduction & Industrial Context
In small food processing (e.g. snack manufacturing, confectionery, bakery):
1. **Raw Material Leakage:** Subtle physical changes—such as ambient humidity variations affecting dough flour hydration, or thermostat drift in deep fryers increasing palmolein oil absorption—generate steady 3–8% cost increases that are difficult to detect on a single batch.
2. **Packaging Mismatches:** Damaged pouches and unboxed finished packets routinely accumulate in production staging areas, creating phantom inventory and carton reconciliation discrepancies.
3. **Black-Box AI Limitations:** Modern deep learning models cannot be audited in court or tax assessments, often hallucinate causes, and fail under low-sample-size regimes ($N < 30$).

---

## 2. Core Architectural Innovations

### 2.1 The 9-Point Forensic Framework
YieldTrace implements a structured diagnostic pipeline for every batch:

```
[Production Batch Execution]
           │
           ▼
[Standard vs. Actual Comparison] ──► What was expected? What happened?
           │
           ▼
[Material & Yield Variance]      ──► Where did deviation occur? How large?
           │
           ▼
[Sample-Size Disciplined Baseline]─► Is deviation unusual vs. history?
           │
           ▼
[Statistical & Physical Evidence]──► Evidence supporting finding?
           │
           ▼
[Supervisor Actionable Advice]   ──► Root-cause investigation guidance
           │
           ▼
[Financial Impact Attribution]   ──► Cost effect at standard baseline
           │
           ▼
[Immutable Audit Ledger Trace]   ──► Source document & movement trace
```

### 2.2 Sample-Size Fallback Discipline
A major pitfall in industrial statistics is claiming statistical confidence when sample counts are inadequate. YieldTrace enforces an explicit sample-size threshold:
- For $N < 10$: The engine flags `is_reliable = False`, emits the transparent notice *"Baseline not yet reliable – insufficient historical observations"*, and uses a conservative 3% engineering tolerance.
- For $N \ge 10$: The engine computes robust location and dispersion metrics: Sample Mean, Sample Standard Deviation, Median, and Median Absolute Deviation (MAD), establishing a $2\sigma$ control envelope.

### 2.3 Sequential Drift Detection via Tabular CUSUM
While Shewhart control charts detect large transient spikes, they often fail to capture subtle, persistent shifts (e.g., a 0.5 litre excess oil absorption per batch). YieldTrace uses a two-sided Tabular CUSUM:
$$S_i^{+} = \max(0, S_{i-1}^{+} + (X_i - \mu_0 - k))$$
$$S_i^{-} = \min(0, S_{i-1}^{-} + (X_i - \mu_0 + k))$$
Where $k = 0.5\sigma$ and $h = 3.0\sigma$. When $S_i^{+} > h$, the engine issues an early warning before cumulative financial loss escalates.

### 2.4 Packaging Reconciliation Non-Coercion
In typical ERP systems, if 188 packets are produced and carton capacity is 20, the software automatically coerces the carton count to $\lceil 188/20 \rceil = 10$. If the warehouse only issued 9 cartons, this silent correction corrupts carton inventory balances. YieldTrace preserves the actual 9-carton issue, displays 180 boxed capacity, flags 8 unboxed packets, and generates an immutable audit warning.

---

## 3. Mathematical Reconciliation Guarantee
The cost bridge equation:
$$\text{Actual Batch Cost} = \text{Standard BOM Baseline} + \text{Price Variance} + \text{Usage Variance} + \text{Overhead Variance}$$
YieldTrace uses Python `Decimal` arithmetic with banking rounding, ensuring that the reconciliation discrepancy is identically **₹0.00**.

---

## 4. Conclusion
YieldTrace demonstrates that explainable, mathematically rigorous intelligence combined with immutable ledger mechanics provides vastly superior operational utility for small manufacturers compared to generic AI chatbots or static legacy ERPs.
