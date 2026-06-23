# Blueprint 03 - Invoicing & Billing: Real-Data Validation Report

- **Dataset:** UCI Machine Learning Repository - *Online Retail II*
- **Period:** 2009-12
- **Tax rate:** 8%  |  **Payment terms:** 30 days  |  **as_of:** 2010-03-01
- **Customers invoiced:** 3
- **Total billed:** $ 2,015.58
- **Overdue (as_of):** 3
- **Reconciliation (engine vs independent recompute, within $0.01):** **PASS**

## Rows skipped (logged, never silent)

Total skipped: **6**

| Reason | Count |
|---|---|
| non-positive Quantity (returns/credits) | 2 |
| missing Customer ID | 2 |
| non-numeric / blank Price | 2 |
| outside target period | 0 |

## Per-customer reconciliation

| Customer | Lines | Subtotal | Tax | Total | Engine vs Recompute | Reminders fired |
|---|---|---|---|---|---|---|
| 13078 | 22 | $ 794.53 | $ 63.56 | $ 858.09 | PASS | 3, 7, 14 |
| 13085 | 18 | $ 805.70 | $ 64.46 | $ 870.16 | PASS | 3, 7, 14 |
| 15362 | 20 | $ 266.05 | $ 21.28 | $ 287.33 | PASS | 3, 7, 14 |

## How it works

1. Real Online Retail II rows are ingested and shaped into the blueprint's `UsageRecord` (adapter.py). Returns, missing Customer IDs and blank/zero prices are dropped and counted by reason.
2. One invoice per customer is built by the blueprint engine (`src.invoicing.build_invoice`) - that code is reused, not reimplemented.
3. An **independent** recomputation (`subtotal = sum(qty*price)`, `tax = subtotal*rate`, `total = subtotal+tax`) cross-checks the engine within $0.01.
4. The blueprint reminder engine (`src.reminders`) determines overdue invoices and which escalation offsets [3, 7, 14] have fired by `as_of`.

