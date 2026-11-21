# YieldTrace — Production Variance Forensics & Audit Platform

> **"Every gram accounted for. Every deviation explained."**

**YieldTrace** is an intelligent, ledger-driven manufacturing ERP, Production Variance Forensics, and Audit Intelligence platform designed specifically for small food manufacturers. Submitted to the **National Institute of Technology Tiruchirappalli (NIT Trichy), Centre for Digital Infrastructure, Winter Internship 2026**.

---

## 1. Problem Statement & Distinguishing Innovation

Small and medium-scale food manufacturers face chronic margin erosion from unexplained production leaks:
- Raw material over-consumption (e.g. fryer oil absorption, spice over-dosing).
- Substandard packet yields due to extrusion or packaging tearing.
- Packaging reconciliation mismatches (unboxed packets remaining in staging).
- Inventory discrepancies caused by arbitrary stock balance overwriting.

Ordinary ERPs merely track stock levels; generic AI tools hallucinate unverified causes. **YieldTrace's core innovation is Production Variance Forensics**: an explainable decision-support engine grounded in standard costing accounting and statistical process control (CUSUM) that answers **9 critical questions**:
1. *What was expected to happen?* (Standard BOM baseline)
2. *What actually happened?* (Actual batch consumption and good output)
3. *Where did the deviation occur?* (Specific raw material, process station, or packaging stage)
4. *How large was the deviation?* (Absolute and percentage variance)
5. *Is this deviation unusual compared with historical production?* (Sample-size disciplined baseline)
6. *What evidence supports the finding?* (Statistical 2-sigma vs. deterministic 3% tolerance fallback)
7. *What should the production supervisor investigate?* (Domain-specific root-cause guidance)
8. *What is the financial impact?* (Cost impact evaluated against standard baseline)
9. *Can the complete result be traced back to source transactions?* (Full audit trace to immutable ledger moves)

---

## 2. Canonical NIT Benchmark Verification

Tested and verified against the canonical Murukku 200 g benchmark:

| Metric / Item | Benchmark Specification | YieldTrace Calculated Result | Status |
| :--- | :--- | :--- | :--- |
| **Product** | Murukku 200 g (`FG-MURUKKU-200G`) | Murukku 200 g | ✅ Verified |
| **Flour Closing Balance** | 100 kg + 60 kg (Purchase) - 40 kg (Run) | **120.0 kg** | ✅ Exact Match |
| **Cooking Oil Balance** | 30.0 L - 10.5 L | **19.5 litres** | ✅ Exact Match |
| **Spice Mix Balance** | 5.0 kg - 1.2 kg | **3.8 kg** | ✅ Exact Match |
| **Printed Pouches** | 500 - 188 (Good) - 6 (Damaged) | **306 pieces** | ✅ Exact Match |
| **Cartons Balance** | 30 - 9 (Issued) | **21 cartons** | ✅ Exact Match |
| **Finished Murukku Stock** | Opening 50 + Produced 188 = 238 pkts | **238 packets** | ✅ Exact Match |
| **After Retailer A Dispatch** | 238 - 150 pkts dispatched | **88 packets** | ✅ Exact Match |
| **After Distributor B Fulfillment** | 88 - 88 pkts dispatched (32 backordered) | **0 packets** (No negative stock) | ✅ Exact Match |
| **Oil Consumption Variance** | Standard 10.0 L vs Actual 10.5 L | **+5.0%** (Unfavorable) | ✅ Exact Match |
| **Production Yield Variance** | Planned 200 pkts vs Actual 188 pkts | **-6.0%** (Yield loss: 12 pkts) | ✅ Exact Match |
| **Packaging Reconciliation** | 9 Cartons &times; 20 capacity = 180 boxed | **8 unboxed packets** | ✅ Preserved (Not 10) |
| **Retailer A Invoice** | 150 pkts &times; ₹50 = ₹7,500 + 5% GST | **₹7,875.00** (CGST ₹187.50, SGST ₹187.50) | ✅ Exact Match |
| **Retailer A Outstanding** | Total ₹7,875 - ₹4,000 paid | **₹3,875.00** | ✅ Exact Match |
| **Distributor B Invoice** | 88 pkts &times; ₹50 = ₹4,400 + 5% IGST | **₹4,620.00** (IGST ₹220.00) | ✅ Exact Match |
| **Distributor B Backorder** | Ordered 120 - Fulfilled 88 | **32 packets shortage** | ✅ Exact Match |
| **Cost Waterfall Discrepancy** | Exact mathematical reconciliation | **₹0.00 (Zero paisa discrepancy)** | ✅ Exact Match |

---

## 3. Technology Stack

- **Backend:** Python 3.13+, FastAPI, SQLAlchemy ORM, Pydantic v2.
- **Database:** SQLite (local development & in-memory tests), PostgreSQL-ready.
- **Data & Statistics:** NumPy, Pandas (CUSUM, robust Median/MAD, Mean/StdDev).
- **Frontend:** HTML5, CSS3 (Custom SaaS Design System), Vanilla ES6 JavaScript, Bootstrap 5, Chart.js 4.4.
- **Reporting & Compliance:** ReportLab (Dynamic PDF), OpenPyXL (Excel spreadsheets), Python CSV engine.
- **Test Automation:** Pytest, HTTPX, Starlette TestClient (11/11 tests passing).

---

## 4. Getting Started & Installation

### Clone & Setup Virtual Environment
```bash
# Clone the repository
git clone https://github.com/your-username/YieldTrace.git
cd YieldTrace

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Seed Canonical Data
```bash
# Seed official NIT Tiruchirappalli benchmark
python -m seed.seed_data

# Seed reproducible synthetic historical dataset (40 runs, Seed=42)
python -m seed.historical_runs
```

### Run Automated Tests
```bash
pytest -v
```

### Start the Application Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Open your browser at `http://127.0.0.1:8000` to access the YieldTrace portal. Interactive Swagger API documentation is available at `http://127.0.0.1:8000/docs`.

---

## 5. Demo User Accounts

YieldTrace enforces Role-Based Access Control (RBAC) across 6 roles:

| Role | Username | Password | Operational Access Scope |
| :--- | :--- | :--- | :--- |
| **Owner** | `owner` | `Password@123` | Full executive, operational, and financial control |
| **Administrator** | `admin` | `Password@123` | System configuration, master data, user accounts |
| **Salesman** | `sales_lead` | `Password@123` | Customer management, sales orders (restricted from costing) |
| **Production Supervisor**| `prod_supervisor` | `Password@123`| Production execution, batch scrap recording, BOM lines |
| **Accountant** | `accountant` | `Password@123` | GST invoicing, payment recording, receivables ledger |
| **Auditor** | `auditor` | `Password@123` | Read-only inspection of stock ledger, audit logs, and forensics |

---

## 6. Project Architecture

```
YieldTrace/
├── app/
│   ├── main.py                     # FastAPI entry point & routes
│   ├── database.py                 # SQLite/PostgreSQL connection engine
│   ├── models.py                   # 24 relational models & indices
│   │
│   ├── modules/
│   │   ├── auth/                   # PBKDF2 password hashing & RBAC
│   │   ├── master/                 # Products, Customers, Suppliers, Units
│   │   ├── inventory/              # Immutable append-only ledger & WAUC
│   │   ├── purchases/              # Procurement, goods receipt, idempotency
│   │   ├── production/             # BOM execution, variances & packaging audit
│   │   ├── sales/                  # Orders, approval, backorders, GST billing
│   │   ├── costing/                # Cost waterfall mathematical bridge
│   │   ├── insight/                # Variance Forensics & Deterministic Planner
│   │   ├── reports/                # 14 reports (CSV, Excel, PDF)
│   │   └── dashboard/              # Dynamic real-time KPI aggregations
│   │
│   ├── templates/
│   │   └── index.html              # Clean, light-themed SaaS dashboard
│   └── static/
│       ├── css/style.css           # Premium enterprise UI stylesheet
│       └── js/app.js               # Reactive Chart.js & API orchestration
│
├── seed/
│   ├── seed_data.py                # Canonical NIT benchmark dataset
│   └── historical_runs.py          # 40 reproducible synthetic runs (Seed=42)
│
├── tests/
│   ├── conftest.py                 # Test database fixtures
│   ├── test_benchmark.py           # Canonical benchmark assertions
│   ├── test_inventory.py           # Invariance & negative stock guards
│   ├── test_production.py          # Packaging reconciliation warning test
│   ├── test_forensics.py           # Baseline fallbacks & CUSUM drift
│   ├── test_planner.py             # Feasibility & deficit analysis
│   └── test_security.py            # Hashing & RBAC permissions
│
└── docs/
    ├── design_note.md              # Mathematical formulas & architecture
    ├── innovation_note.md          # Variance Forensics research paper
    ├── benchmark_verification.md   # Exact canonical verification tables
    └── demo_script.md              # 8-minute NIT evaluator walkthrough
```

---

## 7. License & Authorship

Developed for the **National Institute of Technology Tiruchirappalli (NIT Trichy), Centre for Digital Infrastructure, Winter Internship 2026**.
All rights reserved &copy; 2026 YieldTrace Engineering Team.
