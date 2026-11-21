# YieldTrace

> Precision Production, Inventory Ledger & Variance Forensics Engine

YieldTrace is a production yield tracking and variance accounting system designed for manufacturing and packaging operations.

## Core Architectural Principles

1. **Standard BOM vs. Weighted-Average Costing**:
   - **Standard BOM Cost**: Reference baseline for consumption and yields.
   - **Weighted-Average Valuation**: Actual purchase cost calculation.
   - **Price Variance**: Impact of raw material purchase-price deviations.
   - **Usage Variance**: Impact of excess or reduced raw material consumption.
   - **Yield Variance**: Impact of producing fewer or more good units compared to input recipe expectations.
   - **Overhead**: Systematically allocated across production runs without double counting.

2. **Immutable Append-Only Stock Ledger**:
   - Stock balances are NEVER directly updated or overwritten.
   - Stock levels are calculated by summing signed movements from `stock_moves`.
   - Every movement records item, quantity, direction (`IN` / `OUT`), unit cost, reference document, and timestamp.

3. **Packaging Reconciliation & Audit Warnings**:
   - Tracks actual good packets produced vs. carton capacity.
   - Automatically detects and flags mismatches (e.g. unboxed packets, carton capacity discrepancies).
   - Preserves actual transaction data instead of silently coercing carton numbers.

## Day 1 Architecture & Milestones

- **FastAPI Backend** with SQLAlchemy ORM and SQLite (PostgreSQL-ready).
- **Relational Schema**: items, unit_conversions, suppliers, customers, boms, bom_lines, purchases, production_runs, run_consumption, run_output, stock_moves, overheads, audit_logs.
- **NIT Benchmark Verification**:
  - Purchase transactions (e.g., 60 kg flour @ ₹45/kg).
  - Production run consuming flour, oil, pouches, and packing into cartons.
  - Verification of 120 kg flour, 19.5L oil, 306 pouches, 21 cartons, 238 good packets with packaging mismatch warning.
