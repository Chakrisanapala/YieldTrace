# YieldTrace — Comprehensive Financial & Costing Validation

**Project:** YieldTrace — Intelligent Production, Variance Forensics and Audit Intelligence Platform  
**Target Evaluation:** National Institute of Technology Tiruchirappalli (NIT Trichy), Centre for Digital Infrastructure  
**Internship:** Winter Internship 2026  
**Auditor:** Accounting & Costing Validation Team  
**Standard:** Indian Accounting Standard (Ind AS 2) & Goods and Services Tax (GST) Act 2017  
**Validation Status:** VERIFIED (₹0.00 Paisa Discrepancy)  

---

## 1. Overview & Objectives

In food manufacturing, standard costing establishes target baselines, but actual procurement volatility, material losses, and packaging anomalies create variances. The objective of this validation is to mathematically verify that YieldTrace:
1. Correctly values inventory under the **Moving Weighted-Average Unit Cost (WAUC)** method.
2. Formulates and executes the **Standard Bill of Materials (BOM)** baseline without recipe distortion.
3. Separates **Price Variance**, **Usage Variance**, and **Yield Variance** without double-counting losses.
4. Generates an exact **Cost Waterfall Reconciliation** that sums to the actual batch cost with ₹0.00 discrepancy.
5. Preserves transactional reality in **Packaging Reconciliation** (flags unboxed packets rather than silently coercing carton counts).
6. Calculates **Goods and Services Tax (GST)** accurately across intra-state (CGST + SGST) and inter-state (IGST) jurisdictions.
7. Enforces physical inventory constraints during **Backorder Allocation** without allowing negative balances.

---

## 2. Canonical NIT Benchmark Formulation

### 2.1 Finished Good Master
* **Product Name:** Murukku 200 g
* **Item Code:** `FG-MURUKKU-200G`
* **Selling Price:** ₹50.00 per packet
* **Standard Cost:** ₹25.80 per packet
* **GST Rate:** 5.0% (HSN 21069099)

### 2.2 Standard Bill of Materials (BOM-MURUKKU-200G-V1)
* **Standard Batch Output:** 200 packets
* **Carton Capacity:** 20 packets per carton
* **Standard Overheads:** ₹1,800.00 per batch (Labour ₹1,200.00 + Gas/Electricity ₹600.00)

> [!NOTE] Demonstration & Baseline Assumptions
> The standard material prices (₹40.00/kg flour, ₹110.00/L oil, ₹250.00/kg spice mix, ₹1.50/pouch, ₹25.00/carton), planned BOM recipe quantities (40 kg flour, 10 L oil, 1 kg spice, 200 pouches, 10 cartons), wholesale selling price (₹50.00/packet), and standard batch overheads (₹1,800.00: ₹1,200 labour + ₹600 utilities) are configured demonstration assumptions and operational baselines established in YieldTrace to calculate standard-cost vs. actual-cost variances. They are not official specifications mandated by NIT Trichy.

| BOM Component | Item Code | Standard Qty | Unit | Standard Rate (₹) | Standard Cost (₹) |
|---|---|---|---|---|---|
| Flour | `RM-FLOUR` | 40.0 | kg | ₹40.00 | ₹1,600.00 |
| Cooking Oil | `RM-OIL` | 10.0 | litres | ₹110.00 | ₹1,100.00 |
| Spice Mix | `RM-SPICE-MIX` | 1.0 | kg | ₹250.00 | ₹250.00 |
| Printed Pouches | `PK-POUCH-200G` | 200.0 | pieces | ₹1.50 | ₹300.00 |
| Cartons | `PK-CARTON-20PK` | 10.0 | cartons | ₹25.00 | ₹250.00 |
| Standard Overheads | Overheads | 1.0 | batch | ₹1,800.00 | ₹1,800.00 |
| **Total Standard Batch Cost** | | | | | **₹5,300.00** |
| **Standard Cost per Packet** | | | | | **₹26.5000** |

---

## 3. Step-by-Step Transaction Walkthrough & Mathematical Proofs

### Milestone 1: Opening Inventory Ledger State

Opening stock is posted directly through append-only stock movements (`INIT`):

| Item Code | Description | Category | Opening Balance | Standard Cost | Initial Valuation |
|---|---|---|---|---|---|
| `RM-FLOUR` | Flour | Raw Material | 100.0 kg | ₹40.00 | ₹4,000.00 |
| `RM-OIL` | Cooking Oil | Raw Material | 30.0 L | ₹110.00 | ₹3,300.00 |
| `RM-SPICE-MIX` | Spice Mix | Raw Material | 5.0 kg | ₹250.00 | ₹1,250.00 |
| `PK-POUCH-200G` | Printed Pouches | Packaging | 500.0 pcs | ₹1.50 | ₹750.00 |
| `PK-CARTON-20PK` | Cartons | Packaging | 30.0 cartons | ₹25.00 | ₹750.00 |
| `FG-MURUKKU-200G` | Finished Murukku | Finished Good | 50.0 pkts | ₹20.00 | ₹1,000.00 |
| **Total Initial Stock Valuation** | | | | | **₹11,050.00** |

---

### Milestone 2: Procurement & Moving Weighted-Average Cost Update

A purchase receipt is recorded from **Annapurna Agro Mills** (Invoice `#INV-NIT-FLOUR-60`):
* **Quantity Received:** 60.0 kg Flour
* **Purchase Price:** ₹45.00 per kg
* **Total Purchase Amount:** ₹2,700.00

#### Mathematical Derivation of Flour WAUC:
$$\text{Old Total Value} = 100.0\text{ kg} \times ₹40.00\text{/kg} = ₹4,000.00$$
$$\text{New Receipt Value} = 60.0\text{ kg} \times ₹45.00\text{/kg} = ₹2,700.00$$
$$\text{Total Quantity} = 100.0 + 60.0 = 160.0\text{ kg}$$
$$\text{New WAUC} = \frac{₹4,000.00 + ₹2,700.00}{160.0\text{ kg}} = \frac{₹6,700.00}{160.0} = \mathbf{₹41.875\text{/kg}}$$

* **Verified Ledger Balance:** 160.0 kg
* **Verified WAUC:** ₹41.875/kg (Exact 3-decimal precision preserved)

---

### Milestone 3: Production Run Execution (Batch #RUN-NIT-MURUKKU-001)

The production supervisor reports actual execution data for 1 planned batch of Murukku 200 g:

| Material | Standard Planned | Actual Consumed | Variance (Qty) | Variance (%) | Actual Unit Cost (WAUC) | Actual Cost |
|---|---|---|---|---|---|---|
| Flour | 40.0 kg | 40.0 kg | 0.0 kg | 0.0% | ₹41.875 | ₹1,675.00 |
| Cooking Oil | 10.0 L | 10.5 L | +0.5 L | **+5.0%** | ₹110.000 | ₹1,155.00 |
| Spice Mix | 1.0 kg | 1.2 kg | +0.2 kg | **+20.0%** | ₹250.000 | ₹300.00 |
| Printed Pouches* | 200.0 pcs | 194.0 pcs | -6.0 pcs | -3.0% | ₹1.500 | ₹291.00 |
| Cartons | 10.0 cartons | 9.0 cartons | -1.0 carton | -10.0% | ₹25.000 | ₹225.00 |
| Actual Overheads | ₹1,800.00 | ₹1,800.00 | ₹0.00 | 0.0% | N/A | ₹1,800.00 |
| **Total Batch Cost** | | | | | | **₹5,446.00** |

*\*Note: Actual pouch consumption is 194.0 pcs (188 good packets + 6 damaged pouches = 194 pcs). The 6 damaged pouches are tracked for quality forensics and scrap reporting, but are not added as a separate financial penalty to prevent double-counting.*

#### Finished Goods Output & Yield Variance:
* **Standard Expected Output:** 200.0 packets
* **Actual Good Packets Produced:** 188.0 packets
* **Yield Loss:** $200 - 188 = 12$ packets
* **Yield Variance:**
  $$\text{Yield Variance \%} = \frac{188 - 200}{200} \times 100 = \mathbf{-6.0\%}$$

#### Packaging Reconciliation (Non-Coercion Audit):
* **Cartons Issued:** 9 cartons
* **Carton Packing Capacity:** 20 packets/carton
* **Maximum Boxed Capacity:** $9 \times 20 = 180$ packets
* **Good Output:** 188 packets
* **Unboxed Packets:** $188 - 180 = \mathbf{8\text{ packets}}$
* **Audit System Response:** Preserves 9 cartons in stock ledger. Generates warning:
  `AUDIT_WARNING: Packaging capacity (180 pkts) is less than good packets produced (188 pkts). 8 packets remain unboxed.`
  **Does NOT silently coerce cartons to 10.**

---

### Milestone 4: Mathematical Cost Waterfall Reconciliation

The cost bridge demonstrates how the standard BOM cost baseline transforms into the actual batch cost:

$$\text{Actual Batch Cost} = \text{Standard Cost} + \text{Material Price Variance} + \text{Material Usage Variance} + \text{Overhead Variance}$$

1. **Standard Baseline Cost:**
   $$\text{Std Cost} = (40 \times 40) + (10 \times 110) + (1 \times 250) + (200 \times 1.50) + (10 \times 25) + 1800 = \mathbf{₹5,300.00}$$

2. **Material Price Variance:**
   $$\text{Price Variance} = \sum (\text{Actual WAUC} - \text{Standard Price}) \times \text{Actual Quantity}$$
   * Flour: $(41.875 - 40.00) \times 40.0 = +₹75.00$
   * Other items: WAUC equals standard cost $\implies ₹0.00$
   * **Total Price Variance:** $\mathbf{+₹75.00}$ (Unfavorable)

3. **Material Usage Variance (Zero Double-Counting Proof):**
   $$\text{Usage Variance} = \sum (\text{Actual Qty} - \text{Standard Qty}) \times \text{Standard Price}$$
   * Flour: $(40.0 - 40.0) \times 40.00 = ₹0.00$
   * Oil: $(10.5 - 10.0) \times 110.00 = +₹55.00$
   * Spice Mix: $(1.2 - 1.0) \times 250.00 = +₹50.00$
   * Pouches: $(194.0 - 200.0) \times 1.50 = \mathbf{-₹9.00}$ *(194 actual pouches consumed includes 188 good packets + 6 damaged pouches; no auxiliary scrap charge is added to prevent double-counting)*
   * Cartons: $(9.0 - 10.0) \times 25.00 = \mathbf{-₹25.00}$
   * **Total Net Usage Variance:** $0.00 + 55.00 + 50.00 - 9.00 - 25.00 = \mathbf{+₹71.00}$ (Unfavorable)

4. **Overhead Variance:**
   $$\text{Actual Overheads} - \text{Standard Overheads} = ₹1,800.00 - ₹1,800.00 = \mathbf{₹0.00}$$

5. **Waterfall Summary:**
   $$\text{Total Net Variance} = \text{Price Variance (+₹75.00)} + \text{Usage Variance (+₹71.00)} + \text{Overhead Variance (₹0.00)} = \mathbf{+₹146.00}$$
   $$\text{Reconciled Actual Batch Cost} = \text{Standard Cost (₹5,300.00)} + \text{Total Variance (+₹146.00)} = \mathbf{₹5,446.00}$$
   $$\text{Actual Incurred Batch Cost from Physical Ledger} = \mathbf{₹5,446.00}$$
   $$\mathbf{\text{Discrepancy}} = ₹5,446.00 - ₹5,446.00 = \mathbf{₹0.0000}$$

---

### Milestone 5: Sales Order Allocation, GST Invoicing & Backorders

#### Customer 1: Retailer A (Tamil Nadu — Intra-State)
* **Sales Order:** `#SO-NIT-RETAILER-A`
* **Ordered Quantity:** 150 packets @ ₹50.00
* **Inventory Check:** $50 \text{ (Opening)} + 188 \text{ (Produced)} = 238 \text{ packets available} \ge 150 \implies$ **Full Fulfillment**.
* **Dispatched:** 150 packets
* **Tax Jurisdiction:** Tamil Nadu $\to$ Tamil Nadu (**Intra-State**)
* **GST Calculation:**
  $$\text{Taxable Amount} = 150 \times ₹50.00 = ₹7,500.00$$
  $$\text{CGST (2.5\%)} = 7500 \times 0.025 = ₹187.50$$
  $$\text{SGST (2.5\%)} = 7500 \times 0.025 = ₹187.50$$
  $$\text{IGST (5.0\%)} = ₹0.00$$
  $$\text{Total Invoice Amount} = ₹7,500.00 + ₹187.50 + ₹187.50 = \mathbf{₹7,875.00}$$
* **Payment Received:** ₹4,000.00 (Receipt `#REC-NIT-RET-A`)
* **Outstanding Receivable:** $₹7,875.00 - ₹4,000.00 = \mathbf{₹3,875.00}$
* **Finished Goods Balance After Retailer A:** $238 - 150 = \mathbf{88\text{ packets}}$

---

#### Customer 2: Distributor B (Karnataka — Inter-State)
* **Sales Order:** `#SO-NIT-DISTRIBUTOR-B`
* **Ordered Quantity:** 120 packets @ ₹50.00
* **Inventory Check:** Physical stock available is only **88 packets**.
* **Strict Allocation Logic:**
  * **Fulfilled Quantity:** **88 packets** (All remaining finished goods stock)
  * **Backordered Quantity:** $120 - 88 = \mathbf{32\text{ packets}}$
  * **Order Status:** `PARTIALLY_FULFILLED`
* **Tax Jurisdiction:** Tamil Nadu $\to$ Karnataka (**Inter-State**)
* **GST Calculation (on 88 packets dispatched):**
  $$\text{Taxable Amount} = 88 \times ₹50.00 = ₹4,400.00$$
  $$\text{CGST} = ₹0.00, \quad \text{SGST} = ₹0.00$$
  $$\text{IGST (5.0\%)} = 4400 \times 0.05 = ₹220.00$$
  $$\text{Total Invoice Amount} = ₹4,400.00 + ₹220.00 = \mathbf{₹4,620.00}$$
* **Payment Received:** ₹0.00
* **Outstanding Receivable:** ₹4,620.00
* **Finished Goods Balance After Distributor B:** $88 - 88 = \mathbf{0\text{ packets}}$

---

## 4. Canonical Closing Balances Reconciliation Table

| Material / Item | Opening | Purchases | Production Issue | Production Output | Dispatches | Final Closing Balance | Unit |
|---|---|---|---|---|---|---|---|
| Flour | 100.0 | +60.0 | -40.0 | - | - | **120.0** | kg |
| Cooking Oil | 30.0 | - | -10.5 | - | - | **19.5** | litres |
| Spice Mix | 5.0 | - | -1.2 | - | - | **3.8** | kg |
| Printed Pouches | 500.0 | - | -194.0 | - | - | **306.0** | pieces |
| Cartons | 30.0 | - | -9.0 | - | - | **21.0** | cartons |
| Finished Murukku 200g | 50.0 | - | - | +188.0 | -238.0 (150+88) | **0.0** | packets |

---

## 5. Audit Conclusion

The financial, inventory, and costing modules of YieldTrace conform strictly to canonical ground truth. Decimal calculations ensure that rounding errors and fractional discrepancies are eliminated. The system is verified for academic and professional presentation at NIT Tiruchirappalli.
