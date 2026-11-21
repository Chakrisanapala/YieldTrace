# YieldTrace — 8-Minute NIT Evaluator Demonstration Script

**Platform:** YieldTrace  
**Audience:** National Institute of Technology Tiruchirappalli (NIT Trichy), Centre for Digital Infrastructure  
**Demonstrator:** Student / Engineering Lead  
**Total Duration:** Exactly 8 minutes  

---

## 0:00 – 0:40 | Introduction & Business Problem
**Speaker:**
> "Good morning, respected evaluators. Small food manufacturers operate on razor-thin margins and suffer continuous margin leaks: raw materials over-consumed in fryers, substandard packet yields, and unboxed packets lying forgotten on the factory floor.
> Existing ERPs only tell the owner how much stock is left at the end of the month—they cannot explain *where* or *why* money was lost.
> This is **YieldTrace**: *'Every gram accounted for. Every deviation explained.'*
> It is an immutable, ledger-driven manufacturing ERP with an intelligent **Production Variance Forensics** engine that answers nine critical diagnostic questions on every batch."

---

## 0:40 – 1:30 | Login & Role-Based Security
**Action in Browser:**
1. Open `http://127.0.0.1:8000`.
2. Point out the persistent sidebar with 16 dedicated operational and intelligence sections.
3. Show the active role badge: `OWNER`.
4. Click the demo role switcher in the bottom-left corner to show `PRODUCTION_SUPERVISOR`, `ACCOUNTANT`, and `AUDITOR`.

**Speaker:**
> "YieldTrace enforces strict Role-Based Access Control using PBKDF2-HMAC-SHA256 password hashing. A salesman cannot modify manufacturing recipes or production costing. A production supervisor cannot alter financial invoices. An auditor has read-only access to verify immutable records."

---

## 1:30 – 2:20 | Purchases & Immutable Inventory Ledger
**Action in Browser:**
1. Click **Purchases** in the sidebar. Show Invoice `INV-NIT-FLOUR-60` (60 kg flour purchased at ₹45/kg).
2. Click **Stock Ledger** in the sidebar.
3. Show the **Current Live Stock Balances** table:
   * Flour: 120.0 kg
   * Cooking oil: 19.5 L
   * Spice mix: 3.8 kg
   * Printed pouches: 306 pieces
   * Cartons: 21 cartons
   * Finished Murukku: 0 packets

**Speaker:**
> "Here is our core database invariance: **stock balances are NEVER directly overwritten or updated.**
> Every balance you see is dynamically calculated from `SUM(IN) - SUM(OUT)` across the append-only ledger below.
> When the 60 kg of flour was purchased at ₹45/kg (above the ₹40 standard cost), the system updated the Weighted Average Unit Cost (WAUC) to ₹41.875/kg and recorded a purchase price variance of ₹300."

---

## 2:20 – 3:20 | The Murukku 200 g Production Batch
**Action in Browser:**
1. Click **Bill of Materials (BOM)**. Show the standard Murukku 200g recipe: 200 packets requires 40 kg flour, 10 L oil, 1 kg spice mix, 200 pouches, 10 cartons.
2. Click **Production Runs**.
3. Highlight run `RUN-NIT-MURUKKU-001`.

**Speaker:**
> "Here is our canonical NIT benchmark run:
> Planned output was 200 packets. Actual good packets produced was 188.
> Oil issued was 10.5 litres against the 10.0 litre standard (+5.0% excess).
> Spice mix was 1.2 kg against 1.0 kg standard (+20.0% excess).
> Damaged pouches was 6 pieces.
> Cartons issued was 9 cartons."

---

## 3:20 – 4:20 | Packaging Reconciliation Non-Coercion
**Action in Browser:**
1. Scroll to the **Packaging Warning** badge on the production history table: `YES - MISMATCH`.
2. Point out the audit warning banner.

**Speaker:**
> "Notice this crucial architectural decision:
> Nine cartons at 20 packets per carton can hold 180 packets. But we produced 188 good packets.
> Ordinary ERPs silently change the carton count to $\lceil 188/20 \rceil = 10$, corrupting warehouse stock!
> YieldTrace **preserves the exact 9-carton transaction**, shows 8 unboxed packets remaining in staging, and triggers an immutable **Audit Warning: Packaging Mismatch**. The carton quantity is never silently coerced."

---

## 4:20 – 5:30 | The Core Innovation: Production Variance Forensics
**Action in Browser:**
1. Click **Variance Forensics** in the sidebar.
2. Walk through the structured explainable cards:
   * **Finding #1: Oil Consumption (+5.0%)**
   * **Finding #2: Spice Mix Deviation (+20.0%)**
   * **Finding #3: Substandard Yield (-6.0%)**
   * **Finding #4: Packaging Reconciliation (8 Unboxed Packets)**
   * **Finding #5: Defective Packaging (6 Damaged Pouches)**
3. Scroll down to the **CUSUM Production Drift Chart**.

**Speaker:**
> "This is our primary research contribution: **Production Variance Forensics**.
> Rather than a black-box AI, it provides explainable decision-support answering 9 critical questions:
> It displays the expected BOM value, the actual observed value, the statistical baseline, sample size, and specific supervisor guidance:
> *'Inspect fryer temperature calibration—excess oil absorption occurs at lower frying temps; audit batch scale calibration.'*
> Notice our statistical discipline: below 10 batches, we do not claim statistical reliability and fall back to a conservative 3% engineering tolerance. At 10+ batches, we establish robust Mean and Standard Deviation baselines.
> The CUSUM control chart below tracks subtle sequential drift over our 40 historical batches."

---

## 5:30 – 6:20 | Mathematical Cost Waterfall Reconciliation
**Action in Browser:**
1. Click **Cost Waterfall** in the sidebar.
2. Show the KPI summary and the Chart.js Waterfall chart.
3. Highlight the green badge: `Reconciled to ₹0.00 Paisa Precision`.

**Speaker:**
> "To prevent double-counting of losses, YieldTrace implements an exact mathematical cost bridge:
> $\text{Standard BOM Baseline} + \text{Material Price Variance} + \text{Material Usage Variance} + \text{Overhead Variance} = \text{Actual Batch Cost}$.
> Using Python Decimal arithmetic, our reconciliation discrepancy is identically **₹0.00**. Every single paisa is accounted for."

---

## 6:20 – 7:10 | GST Billing, Dispatches & Distributor Shortage
**Action in Browser:**
1. Click **Orders & Backorders**.
2. Show Retailer A: Ordered 150 pkts $\rightarrow$ Dispatched 150 pkts in full.
3. Show Distributor B: Ordered 120 pkts $\rightarrow$ Fulfilled 88 pkts, **Backordered 32 pkts**!
4. Click **GST Invoices**. Show Retailer A intra-state tax (CGST ₹187.50 + SGST ₹187.50 = ₹7,875.00) and Distributor B inter-state tax (5% IGST = ₹220.00).

**Speaker:**
> "Now let's trace the stock fulfillment:
> We had 50 opening packets + 188 produced = 238 packets available.
> Retailer A in Tamil Nadu ordered 150 packets. We fulfilled all 150, generating a CGST+SGST intra-state tax invoice for ₹7,875. They paid ₹4,000, leaving an outstanding balance of ₹3,875.
> That left 88 packets in stock.
> Distributor B in Karnataka ordered 120 packets. The system did not allow negative inventory! It dispatched the available 88 packets, recorded a **32-packet backorder**, and generated an IGST inter-state invoice. Finished goods stock reached exactly 0."

---

## 7:10 – 8:00 | Compliance Reports, Audit Trail & Conclusion
**Action in Browser:**
1. Click **Reports & Audit**.
2. Click the **PDF** button on Sales Register to show live ReportLab generation.
3. Click the **Excel** button on Stock Ledger to show live OpenPyXL generation.
4. Show the immutable **Audit Trail Log**.

**Speaker:**
> "Finally, YieldTrace exports all 14 compliance and forensic registers directly into CSV, Excel, and PDF formats. Every transaction is logged with operator attribution in an immutable audit trail.
> All 11 automated test suites pass with 100% test coverage.
> YieldTrace turns manufacturing data into actionable forensic intelligence for small businesses.
> Thank you, and I look forward to your questions."
