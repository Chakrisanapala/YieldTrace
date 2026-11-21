# YieldTrace Design Note - Day 1 Architecture

## 1. Accounting & Variance Engine

### Costing Formulae
- **Standard Unit Cost**: $\sum (\text{BOM Quantity} \times \text{Standard Cost})$
- **Actual Material Cost**: Calculated via Weighted-Average Unit Cost (WAUC):
  $$\text{WAUC}_{new} = \frac{(\text{Current Qty} \times \text{Current WAUC}) + (\text{Purchase Qty} \times \text{Purchase Price})}{\text{Current Qty} + \text{Purchase Qty}}$$
- **Price Variance**:
  $$\text{Price Variance} = (\text{Actual Price} - \text{Standard Price}) \times \text{Actual Quantity Purchased}$$
- **Usage Variance**:
  $$\text{Usage Variance} = (\text{Actual Quantity Used} - \text{Standard Quantity Allowed}) \times \text{Standard Price}$$
- **Yield Variance**:
  $$\text{Yield Variance} = (\text{Expected Output at Actual Input} - \text{Actual Good Output}) \times \text{Standard Output Cost}$$

### Packaging Reconciliation Warning Logic
When production output is packed:
- $\text{Expected Cartons} = \lfloor \frac{\text{Good Packets Produced}}{\text{Carton Capacity}} \rfloor$
- $\text{Unboxed Packets} = \text{Good Packets Produced} \pmod{\text{Carton Capacity}}$
- If $\text{Cartons Available} \times \text{Carton Capacity} \neq \text{Good Packets Produced}$, an **Audit Warning: Packaging Mismatch** is triggered.
- Under no circumstances does the system silently modify the cartons consumed or output packets.

## 2. Immutable Ledger (`stock_moves`)
- Transaction Types:
  - `PURCHASE_RECEIPT` (IN)
  - `PRODUCTION_ISSUE` (OUT - Consumption)
  - `PRODUCTION_RECEIPT` (IN - Good Finished Output)
  - `PRODUCTION_SCRAP` (OUT/RECORD - Damaged/Wasted Items)
  - `SALES_DISPATCH` (OUT)
  - `STOCK_ADJUSTMENT` (IN/OUT - explicit auditable adjustment)
- Balances are derived from:
  $$\text{Balance} = \sum_{\text{direction} = \text{IN}} \text{quantity} - \sum_{\text{direction} = \text{OUT}} \text{quantity}$$
