# YieldTrace — NIT Tiruchirappalli Demonstration Readiness & Evaluator Presentation Guide

**Project:** YieldTrace — Intelligent Production, Variance Forensics and Audit Intelligence Platform for Small Food Manufacturers  
**Target Submission:** National Institute of Technology Tiruchirappalli (NIT Trichy), Centre for Digital Infrastructure  
**Internship:** Winter Internship 2026  
**Demonstration Status:** 100% READY FOR DEMONSTRATION  
**Test Suite Verification:** 15 / 15 Passed (100%)  
**Canonical NIT Benchmark:** Reconciled to ₹0.00 Precision  

---

## 1. Demonstration Readiness Checklist

| Readiness Dimension | Verification Requirement | Status | Evidence |
|---|---|---|---|
| **Backend API** | FastAPI application launches without warnings or startup crashes | **READY** | `GET /api/health` returns status: healthy |
| **Database State** | Database seeds canonical NIT benchmark and 40 synthetic runs | **READY** | Verified closing balances: Flour 120 kg, Oil 19.5 L, Finished Goods 0 pkts |
| **Authentication** | PBKDF2-HMAC-SHA256 password security and RBAC token generation | **READY** | All 6 roles authenticated and tested |
| **Frontend UI Shell** | Responsive Single-Page Application (SPA) with 14 functional sections | **READY** | Clean light theme, zero missing assets, Bootstrap 5 responsive layout |
| **Data Visualizations** | Live Chart.js analytics for Cost Waterfall and CUSUM Drift | **READY** | Bar charts and line charts render dynamically |
| **Export Formats** | CSV, Excel (OpenPyXL), and PDF (ReportLab) generation | **READY** | Endpoints return valid downloadable files |
| **Packaging Non-Coercion**| Preserves 9 cartons; flags 8 unboxed packets as immutable warning | **READY** | Audit warning visible on dashboard and production batch history |
| **Mathematical Cost Bridge**| Standard + Price Var + Usage Var + Overhead Var = Actual Cost | **READY** | Verified ₹0.00 discrepancy on Cost Waterfall view |

---

## 2. Exact Terminal Commands to Launch the Application

Follow these exact steps from the project root directory (`d:\Desktop\YieldTrace`):

### Step 1: Activate Virtual Environment
```powershell
.\venv\Scripts\activate
```

### Step 2: Seed the Database with Canonical Benchmark & Historical Runs
```powershell
python seed\seed_data.py
python seed\historical_runs.py
```

### Step 3: Run the Automated Quality & Security Test Suite
```powershell
pytest -v
```
*(Confirms 15 passing test suites covering benchmark, forensics, CUSUM, ledger invariance, negative inventory guards, production planning, and RBAC).*

### Step 4: Launch the High-Performance Web Application
```powershell
uvicorn app.main:app --reload --port 8000
```

### Step 5: Open Browser
Navigate to:
```
http://localhost:8000
```

---

## 3. Step-by-Step 8-Minute Evaluator Demonstration Script

### Minute 1: Project Identity & The Core Manufacturing Problem
* **Action:** Display the YieldTrace topbar and brand banner.
* **Narration to Evaluator:**
  > *"Good morning, respected evaluators. Small food manufacturers in India face a persistent blind spot: standard ERP systems track what happened to inventory balances, but they cannot explain **why** actual production deviated from standard recipes, **who** should investigate, or **how much money** was lost.*
  >
  > *YieldTrace is an intelligent manufacturing ERP, Variance Forensics, and Audit Intelligence platform. Our guiding engineering principle is: **'Every gram accounted for. Every deviation explained.'**"*

---

### Minute 2: Executive Dashboard & Live Operational Status
* **Action:** Click **Overview** in the sidebar.
* **Show Evaluator:**
  1. **Live KPIs:** Total Sales Revenue (₹12,495.00), Average Yield (94.0%), Customer Outstanding (₹8,495.00).
  2. **Highlight Audit Banners:** Point to **Forensic Anomalies Flagged (4)** and **Packaging Mismatches (1)**.
  3. **Operational Audit Trail:** Point to the live event log showing immutable records of inventory movements, production runs, and audit warnings.

---

### Minute 3: Raw Material Procurement & Weighted-Average Valuation
* **Action:** Click **Purchases** in the sidebar, then click **Stock Ledger**.
* **Show Evaluator:**
  1. Invoice `#INV-NIT-FLOUR-60` from *Annapurna Agro Mills* for 60 kg of flour @ ₹45.00/kg.
  2. Explain moving weighted-average valuation:
     $$\text{WAUC} = \frac{(100\text{ kg} \times ₹40.00) + (60\text{ kg} \times ₹45.00)}{160\text{ kg}} = \mathbf{₹41.875\text{/kg}}$$
  3. Show the Stock Ledger view: emphasize that stock balances are derived from `SUM(IN) - SUM(OUT)` across immutable movements, completely prohibiting silent balance overwrites.

---

### Minute 4: Production Run Execution & Packaging Non-Coercion
* **Action:** Click **Production Runs** in the sidebar.
* **Show Evaluator:**
  1. Batch `#RUN-NIT-MURUKKU-001`.
  2. Standard planned yield: 200 packets. Actual good output: 188 packets (Yield Variance: **-6.0%**).
  3. **Packaging Reconciliation:** Cartons used = 9. Capacity = 180 packets. Actual output = 188 packets.
  4. **The Audit Proof:**
     > *"Notice that the system did NOT silently coerce carton quantity from 9 to 10 to make the numbers balance. It recorded the actual 9 cartons issued and raised a prominent audit warning for the 8 unboxed packets. In small food processing, silent software rounding hides theft and packaging miscounts."*

---

### Minute 5: The Core Innovation — Explainable Variance Forensics
* **Action:** Click **Variance Forensics** in the sidebar.
* **Show Evaluator:**
  1. Show the **Explainable Forensic Finding Cards** for Batch `#RUN-NIT-MURUKKU-001`.
  2. Walk through the 9 Critical Forensic Answers:
     - *What was expected?* 10.0 L oil.
     - *What happened?* 10.5 L oil consumed (+5.0% deviation).
     - *Is this unusual?* Yes, exceeds the historical baseline.
     - *What is the statistical method?* Evaluated against 40 historical batches with sample size $N=40$.
     - *What should the supervisor investigate?* Thermostat calibration, frying temperature drop, and oil drainage dwell time.
  3. **CUSUM Production Drift Chart:** Point to the Tabular CUSUM chart below the findings. Show how the $S^+$ statistic detects gradual, persistent upward shifts before they trigger catastrophic quality failures.

---

### Minute 6: Mathematical Cost Waterfall Reconciliation
* **Action:** Click **Cost Waterfall** in the sidebar.
* **Show Evaluator:**
  1. Point to the green verification badge: **"Reconciled to ₹0.00 Paisa Precision"**.
  2. Explain the Cost Bridge:
     $$\text{Standard Baseline Cost (₹5,300.00)} + \text{Price Var (+₹75.00)} + \text{Usage Var (+₹71.00)} = \mathbf{₹5,446.00}$$
     *(Note: Pouch usage variance is $(194 - 200) \times ₹1.50 = -₹9.00$, where 194 includes 188 good + 6 damaged pouches, completely preventing double-counting of damaged packaging).*
  3. Show the interactive Chart.js Waterfall Bar Chart illustrating the step-by-step cost bridge from standard baseline to actual batch cost.

---

### Minute 7: Demand Fulfillment, Backorders & GST Compliance
* **Action:** Click **Orders & Backorders**, then **GST Invoices**.
* **Show Evaluator:**
  1. **Retailer A (Tamil Nadu):** Ordered 150 packets. Dispatched 150 packets. Split into **CGST 2.5% (₹187.50)** and **SGST 2.5% (₹187.50)**.
  2. **Distributor B (Karnataka):** Ordered 120 packets. Physical finished goods stock was only 88 packets.
  3. **The Backorder Proof:**
     > *"YieldTrace strictly enforces physical ledger limits. Instead of creating negative stock or corrupting balances, it dispatched the available 88 packets, generated an inter-state **IGST 5.0% (₹220.00)** invoice, and logged an explicit **32-packet backorder**."*
  4. Finished goods inventory reached exactly **0 packets**.

---

### Minute 8: Production Planner, Role Security & Audit Reports
* **Action:**
  1. Click **Production Planner**: Show the deterministic evaluation calculating net shortage and evaluating raw material feasibility for pending demand.
  2. Switch active demo role to **Salesman**: Attempt to execute an unauthorized action, showing the zero-trust HTTP 403 Forbidden alert.
  3. Click **Reports & Audit**: Show the downloadable **CSV**, **Excel**, and **PDF** export buttons generated via OpenPyXL and ReportLab.
* **Concluding Summary:**
  > *"Every gram accounted for. Every deviation explained. YieldTrace provides a robust, mathematically rigorous, auditable foundation for small food manufacturing."*

---

## 4. Evaluator Q&A and Technical Defensibility

| Likely Evaluator Question | Recommended Technical Defense |
|---|---|
| **"Why not use an off-the-shelf ERP like ERPNext or Odoo?"** | *"Generic ERPs treat manufacturing as basic inventory decrements. They do not separate price vs. usage variance in small food processing, they silently round carton counts, and they lack explainable forensic engines with statistical sample-size guards (N < 10 fallback)."* |
| **"How do you prevent an AI hallucination from reporting false production anomalies?"** | *"The Variance Forensics engine is entirely deterministic and evidence-based. It uses Python statistical functions (mean, standard deviation, median, MAD, and tabular CUSUM) computed strictly over historical ledger records. It never invents physical causes without recorded evidence."* |
| **"What prevents an operator from hacking around negative stock checks in the browser?"** | *"All checks are enforced by backend transactions in Python/SQLAlchemy with row-level locks and `PRAGMA foreign_keys = ON`. The frontend role switcher is purely a demonstration client that sends authenticated Bearer tokens; API endpoints enforce RBAC independently."* |
| **"How is the cost waterfall guaranteed not to count variances twice?"** | *"Material Price Variance evaluates `(Actual WAUC - Standard Rate) * Actual Quantity`. Material Usage Variance evaluates `(Actual Qty - Standard Qty) * Standard Rate`. Because one uses actual quantity and the other uses standard rate, their sum mathematically equals `Actual Total - Standard Total` with zero overlap."* |
