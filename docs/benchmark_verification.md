# Canonical NIT Benchmark Verification Document

**Project:** YieldTrace  
**Evaluation:** NIT Tiruchirappalli, Centre for Digital Infrastructure, Winter Internship 2026  
**Canonical Product:** Murukku 200 g (`FG-MURUKKU-200G`)  
**Automated Test Suite Reference:** `tests/test_benchmark.py::test_canonical_nit_benchmark_complete_flow`  

---

## 1. Input Values

> [!NOTE] Benchmark Specification vs. Configured Demonstration Assumptions
> The canonical scenario specified by NIT Tiruchirappalli defines the physical material flows: opening stock quantities, purchase of 60 kg flour at ₹45/kg, production run producing 188 good packets with 6 damaged pouches and 9 cartons issued (leaving 8 unboxed packets), Retailer A order of 150 packets, and Distributor B order of 120 packets (88 fulfilled, 32 backordered).
> To enable standard-vs-actual variance forensics and mathematical cost waterfall analysis, YieldTrace incorporates standard manufacturing cost baselines (standard material prices: ₹40.00/kg flour, ₹110.00/L oil, ₹250.00/kg spice, ₹1.50/pouch, ₹25.00/carton; standard recipe quantities: 40 kg flour, 10 L oil, 1 kg spice, 200 pouches, 10 cartons; wholesale selling price: ₹50.00/packet; and standard batch overheads: ₹1,800.00 comprising ₹1,200 labour and ₹600 utilities). These configured standard prices, quantities, and overheads are demonstration assumptions designed for realistic variance accounting, not official specifications mandated by NIT Trichy.

### 1.1 Canonical Initial Stock
| Item Code | Description | Category | Unit | Initial Quantity | Unit Cost | Total Valuation |
| :--- | :--- | :--- | :--- | ---: | ---: | ---: |
| `RM-FLOUR` | Flour | Raw Material | kg | 100.0 | ₹40.00 | ₹4,000.00 |
| `RM-OIL` | Cooking oil | Raw Material | litres | 30.0 | ₹110.00 | ₹3,300.00 |
| `RM-SPICE-MIX`| Spice mix | Raw Material | kg | 5.0 | ₹250.00 | ₹1,250.00 |
| `PK-POUCH-200G`| Printed pouches | Packaging | pieces | 500.0 | ₹1.50 | ₹750.00 |
| `PK-CARTON-20PK`| Cartons | Packaging | cartons | 30.0 | ₹25.00 | ₹750.00 |
| `FG-MURUKKU-200G`| Murukku 200 g | Finished Good | packets | 50.0 | ₹20.00 | ₹1,000.00 |
| **Total Opening Valuation** | | | | | | **₹11,050.00** |

---

### 1.2 Purchase Transaction
- **Supplier:** Annapurna Agro Mills (`SUP-FLOUR-01`, Tamil Nadu)
- **Invoice No:** `INV-NIT-FLOUR-60`
- **Item Purchased:** Flour (`RM-FLOUR`)
- **Quantity:** 60.0 kg
- **Unit Price:** ₹45.00 / kg
- **Total Purchase Value:** ₹2,700.00
- **Price Variance:** $(45 - 40) \times 60 = +₹300.00$ (Unfavorable)
- **New Weighted Average Unit Cost (WAUC):**
  $$\text{WAUC} = \frac{(100 \times 40) + (60 \times 45)}{100 + 60} = \frac{4000 + 2700}{160} = ₹41.875 / \text{kg}$$

---

### 1.3 Production Run Benchmark
- **Run Number:** `RUN-NIT-MURUKKU-001`
- **BOM Formulation:** `BOM-MURUKKU-200G-V1` (Batch Size: 1.0, Planned Output: 200 packets)
- **Standard Consumption Requirements vs. Actual Consumed:**
  * Flour: Standard 40.0 kg | Actual 40.0 kg | Variance: 0.0 kg (0.0%)
  * Cooking Oil: Standard 10.0 L | Actual 10.5 L | Variance: +0.5 L (+5.0% Unfavorable)
  * Spice Mix: Standard 1.0 kg | Actual 1.2 kg | Variance: +0.2 kg (+20.0% Unfavorable)
  * Printed Pouches: Standard 200 pcs | Actual 194 pcs (188 good + 6 damaged)
  * Cartons: Standard 10 cartons | Actual Issued: 9 cartons
- **Production Output:**
  * Planned Good Packets: 200.0 packets
  * Actual Good Packets: 188.0 packets
  * Production Yield: $(188 / 200) \times 100 = 94.0\%$
  * Yield Variance: $(188 - 200) / 200 \times 100 = -6.0\%$ (Yield loss: 12 packets)
  * Damaged Pouches: 6 pieces (recorded independently)
- **Production Overheads:**
  * Labour: ₹1,200.00
  * Gas & Electricity: ₹600.00
  * Total Overhead Allocated: ₹1,800.00

---

### 1.4 Packaging Reconciliation Discrepancy
- **Cartons Issued:** 9.0 cartons
- **Carton Capacity:** 20 packets per carton
- **Boxed Capacity:** $9 \times 20 = 180.0$ packets
- **Good Packets Produced:** 188.0 packets
- **Required Cartons (Mathematical):** $\lceil 188 / 20 \rceil = 10.0$ cartons
- **Unboxed Packets:** $188 - 180 = 8.0$ packets
- **System Action:** Preserves the exact 9-carton issue. Generates `AUDIT_WARNING` for packaging mismatch.

---

### 1.5 Sales Orders, Dispatches & Receivables
#### Retailer A (Tamil Nadu — Intra-State)
- **Customer:** Retailer A (Heritage Stores, Chennai)
- **Ordered:** 150 packets @ ₹50.00 / packet
- **Available Stock:** 50 opening + 188 produced = 238 packets
- **Dispatched:** 150 packets in full
- **Taxable Value:** ₹7,500.00
- **GST Rate:** 5% (CGST 2.5% = ₹187.50, SGST 2.5% = ₹187.50)
- **Invoice Total:** ₹7,875.00
- **Payment Received:** ₹4,000.00
- **Customer Outstanding Balance:** ₹3,875.00

#### Distributor B (Karnataka — Inter-State & Shortage Allocation)
- **Customer:** Distributor B (Cauvery Wholesale, Bengaluru)
- **Ordered:** 120 packets @ ₹50.00 / packet
- **Available Stock after Retailer A:** $238 - 150 = 88$ packets
- **Fulfilled Quantity:** 88 packets (dispatched available)
- **Shortage / Backorder:** $120 - 88 = 32$ packets backordered
- **Taxable Value:** $88 \times 50 = ₹4,400.00$
- **GST Rate:** 5% IGST (Inter-state) = ₹220.00
- **Invoice Total:** ₹4,620.00
- **Remaining Finished Goods Inventory:** $88 - 88 = 0.0$ packets (Zero negative stock allowed)

---

## 2. Expected vs. Actual Outputs Verification

| Item / Transaction Stage | Canonical Expected Balance | YieldTrace Output | Verification Method |
| :--- | ---: | ---: | :---: |
| Flour Closing Balance | **120.0 kg** | **120.0 kg** | `SUM(IN) - SUM(OUT)` |
| Cooking Oil Closing Balance | **19.5 litres** | **19.5 litres** | `SUM(IN) - SUM(OUT)` |
| Spice Mix Closing Balance | **3.8 kg** | **3.8 kg** | `SUM(IN) - SUM(OUT)` |
| Printed Pouches Closing Balance | **306 pieces** | **306 pieces** | `SUM(IN) - SUM(OUT)` |
| Master Cartons Closing Balance | **21 cartons** | **21 cartons** | `SUM(IN) - SUM(OUT)` |
| Finished Goods (After Production) | **238 packets** | **238 packets** | `SUM(IN) - SUM(OUT)` |
| Finished Goods (After Retailer A) | **88 packets** | **88 packets** | `SUM(IN) - SUM(OUT)` |
| Finished Goods (After Distributor B)| **0 packets** | **0 packets** | `SUM(IN) - SUM(OUT)` |
| Distributor B Backorder | **32 packets** | **32 packets** | Sales order line state |
| Oil Variance Percentage | **+5.0%** | **+5.0%** | Consumption variance |
| Production Yield Variance | **-6.0%** | **-6.0%** | Yield output equation |
| Unboxed Finished Packets | **8 packets** | **8 packets** | Packaging reconciliation |
| Packaging Audit Warning | **Active Warning** | **Active Warning** | `audit_logs` table |
| Cost Waterfall Reconciliation | **₹0.00 Difference** | **₹0.00 Difference** | `Decimal` bridge assertion |

### 2.1 Cost Waterfall Mathematical Bridge Breakdown
* **Standard BOM Baseline Cost (Planned):** ₹5,300.00
  * Materials: Flour (₹1,600) + Oil (₹1,100) + Spice Mix (₹250) + Pouches (₹300) + Cartons (₹250) = ₹3,500.00
  * Overheads: Labour (₹1,200) + Power (₹600) = ₹1,800.00
* **Price Variance:** $(41.875 - 40.00) \times 40.0\text{ kg} = \mathbf{+₹75.00}$ (Flour WAUC effect)
* **Usage Variance:** $(10.5 - 10) \times 110 + (1.2 - 1) \times 250 + (194 - 200) \times 1.50 + (9 - 10) \times 25 = +55 + 50 - 9 - 25 = \mathbf{+₹71.00}$
* **Overhead Variance:** $₹1,800.00 - ₹1,800.00 = \mathbf{₹0.00}$
* **Total Variance:** $+₹75.00 + ₹71.00 + ₹0.00 = \mathbf{+₹146.00}$
* **Actual Incurred Batch Cost:** $₹5,300.00 + ₹146.00 = \mathbf{₹5,446.00}$
* **Mathematical Discrepancy:** $₹5,446.00 - ₹5,446.00 = \mathbf{₹0.0000}$ (Exact paisa match)

---

## 3. Automated Test Execution
Run the canonical verification test:
```bash
pytest tests/test_benchmark.py -v
```
Output:
```
tests/test_benchmark.py::test_canonical_nit_benchmark_complete_flow PASSED [100%]
```
All canonical benchmark specifications are 100% verified.
