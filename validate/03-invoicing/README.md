# Blueprint 03 - Invoicing & Billing: Real-Data Validation Harness

This harness proves blueprint **03 (invoicing & billing)** works on **real transactions**,
not synthetic fixtures. It ingests genuine retail order lines, aggregates them into invoices
using the blueprint's own engine, and then **independently recomputes the invoice math** to
confirm the engine reconciles to the cent.

## Dataset: UCI "Online Retail II"

Real e-commerce transactions from a UK-based online retailer (gift-ware), 2009-2011. Each row
is one order line.

- **Source:** UCI Machine Learning Repository - *Online Retail II*
  https://archive.ics.uci.edu/dataset/502/online+retail+ii
- **Full download (45 MB xlsx in a zip):**
  https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip
  (two sheets: `Year 2009-2010`, `Year 2010-2011`)
- **License:** Creative Commons Attribution 4.0 (CC BY 4.0) - free for commercial use with attribution.

### Exact real schema (columns, unchanged)

```
Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country
```

### The sample in this repo: `data/online_retail_sample.csv`

**How it was sourced (real path, not hand-authored):** the full UCI zip was downloaded
programmatically, the `Year 2009-2010` sheet was read with pandas/openpyxl, and **66 real rows**
were sliced directly out of the **December 2009** period - exact original values, descriptions,
prices, dates, and country. No values were fabricated.

The sample deliberately includes the **messy rows that occur naturally in this dataset**, so the
hygiene layer is exercised on real data:

- **Negative-Quantity returns** - real credit invoice `C489449` (customer 16321, Australia).
- **Blank Customer ID** - real bulk-adjustment rows (invoices `489464`, `489463`) with no customer.
- **Zero / blank Price** - real `$0.00` lines (e.g. `6 RIBBONS EMPIRE`, `DOOR MAT FAIRY CAKE`).

To regenerate or enlarge the sample, download the full zip above and slice any month you like
into the same 8-column schema.

## What the harness does

1. **`adapter.py`** - maps real Online Retail II rows to the blueprint `UsageRecord`
   (`client_id <- Customer ID`, `description <- Description`, `qty <- Quantity`,
   `unit_price <- Price`, `date <- InvoiceDate`), filters to a target `YYYY-MM` period, and
   groups clean records by Customer ID.
2. **Data hygiene (logged, never silent)** - rows are skipped and **counted by reason**:
   non-positive Quantity (returns/credits), missing Customer ID, non-numeric/blank Price.
3. **`validate.py`** - for each customer it builds an invoice with the blueprint engine
   (`from src.invoicing import build_invoice`, **reused not reimplemented**), then runs an
   **independent recomputation** (`subtotal = sum(qty*price)`, `tax = subtotal*rate`,
   `total = subtotal+tax`) as the cross-check, asserting they reconcile within **$0.01**. It also
   runs the blueprint reminder engine (`src.reminders`) for a chosen `as_of` date to report
   overdue invoices and which escalation offsets fired.
4. Prints an ASCII report (Windows cp1252-safe) and writes **`report.md`**.

The blueprint's `src/` is imported, never modified.

## Run it

```bash
cd validate/03-invoicing
python validate.py
```

Exit code `0` means reconciliation **PASSED**. The path bootstrap (copied from the blueprint's
`run.py` / `conftest.py`) puts the blueprint dir and repo root on `sys.path`, so it works from
this folder with no install step. (Building the sample CSV used `pandas`/`openpyxl`; running the
harness itself needs only the Python standard library.)

## Result on the committed sample

```
Period: 2009-12   Tax rate: 8%   Terms: 30 days   as_of: 2010-03-01
Customers invoiced : 3
Total billed       : $ 2,015.58
Rows skipped       : 6  (2 returns, 2 missing Customer ID, 2 zero-price)
RECONCILIATION (engine vs independent recompute, within $0.01): PASS
```

All three customers reconcile to the cent and are correctly flagged overdue with all reminder
offsets (`3, 7, 14`) fired as of `2010-03-01`.
