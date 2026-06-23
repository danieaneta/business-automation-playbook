"""Real-data validation harness for blueprint 03 (invoicing & billing).

Pipeline:
  1. ingest REAL transactions from the UCI 'Online Retail II' sample CSV,
  2. shape them into blueprint ``UsageRecord``s (adapter.py), with logged hygiene,
  3. build one invoice per customer for a target period via the blueprint engine
     (``src.invoicing.build_invoice`` — we do NOT reimplement it), then
  4. INDEPENDENTLY recompute subtotal/tax/total and assert the engine reconciles
     within a cent (PASS/FAIL per customer + overall),
  5. run the blueprint reminder engine for a chosen ``as_of`` date,
  6. print an ASCII report and write report.md.

ASCII only (Windows cp1252 safe): uses '->' and a plain '$'.

    python validate.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import List, Tuple

# --- sys.path bootstrap (copied from blueprint run.py / conftest.py) ---------
# Put the blueprint dir on the path so `from src.invoicing import ...` resolves,
# and the repo root so `from shared... import ...` would resolve too.
HERE = Path(__file__).resolve().parent
BLUEPRINT_DIR = HERE.parent.parent / "03-invoicing-billing"
REPO_ROOT = HERE.parent.parent
for p in (str(BLUEPRINT_DIR), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

# --- blueprint engine (reused, not reimplemented) ---------------------------
from src.config import DEFAULT_BILLING  # noqa: E402
from src.invoicing import build_invoice  # noqa: E402
from src.models import Invoice  # noqa: E402
from src.reminders import due_reminders, is_overdue  # noqa: E402

# --- local adapter ----------------------------------------------------------
from adapter import SkipLog, group_by_customer, load_records  # noqa: E402


# Knobs for this validation run.
DATA_CSV = HERE / "data" / "online_retail_sample.csv"
PERIOD = "2009-12"          # the real month our sample covers
AS_OF = date(2010, 3, 1)    # well past the Jan-30 due date, so reminders fire
CENT = 0.01


def independent_totals(records, tax_rate: float) -> Tuple[float, float, float]:
    """Recompute money from scratch, independently of the engine.

    subtotal = sum(qty * unit_price) per line (rounded to cents like the engine),
    tax      = subtotal * tax_rate,
    total    = subtotal + tax.
    This is the cross-check — deliberately a separate code path from build_invoice.
    """
    subtotal = 0.0
    for rec in records:
        subtotal += round(rec.qty * rec.unit_price, 2)
    subtotal = round(subtotal, 2)
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)
    return subtotal, tax, total


def reconcile(inv: Invoice, exp: Tuple[float, float, float]) -> Tuple[bool, str]:
    """Compare engine invoice vs independent recomputation within a cent."""
    exp_sub, exp_tax, exp_tot = exp
    checks = [
        ("subtotal", inv.subtotal, exp_sub),
        ("tax", inv.tax, exp_tax),
        ("total", inv.total, exp_tot),
    ]
    bad = [
        f"{name}: engine {got:.2f} != recomputed {want:.2f}"
        for name, got, want in checks
        if abs(got - want) > CENT
    ]
    if bad:
        return False, "; ".join(bad)
    return True, "ok"


def run() -> int:
    rate = DEFAULT_BILLING.tax_rate

    records, skips = load_records(str(DATA_CSV), PERIOD)
    grouped = group_by_customer(records)

    rows: List[dict] = []
    all_pass = True
    overdue_count = 0
    total_billed = 0.0

    for client_id in sorted(grouped):
        recs = grouped[client_id]
        inv = build_invoice(client_id, recs, PERIOD)          # engine
        exp = independent_totals(recs, rate)                  # independent
        ok, detail = reconcile(inv, exp)
        all_pass = all_pass and ok
        total_billed += inv.total

        overdue = is_overdue(inv, AS_OF)
        reminders = due_reminders(inv, AS_OF)
        if overdue:
            overdue_count += 1

        rows.append(
            {
                "client_id": client_id,
                "lines": len(recs),
                "invoice_id": inv.id,
                "subtotal": inv.subtotal,
                "tax": inv.tax,
                "total": inv.total,
                "due_date": inv.due_date.isoformat(),
                "exp_total": exp[2],
                "ok": ok,
                "detail": detail,
                "overdue": overdue,
                "reminders": reminders,
            }
        )

    report = render(rows, skips, all_pass, overdue_count, total_billed, rate)
    sys.stdout.write(report)
    (HERE / "report.md").write_text(render_md(rows, skips, all_pass, overdue_count, total_billed, rate), encoding="utf-8")

    return 0 if all_pass and rows else 1


# ---------------------------------------------------------------------------
# Rendering (ASCII only).
# ---------------------------------------------------------------------------
def _skip_block(skips: SkipLog) -> List[str]:
    lines = [f"Rows skipped (logged, never silent): {skips.total}"]
    for reason, n in skips.as_rows():
        lines.append(f"  - {reason}: {n}")
    return lines


def render(rows, skips, all_pass, overdue_count, total_billed, rate) -> str:
    out: List[str] = []
    bar = "=" * 78
    out.append(bar)
    out.append("BLUEPRINT 03 - INVOICING & BILLING  |  REAL-DATA VALIDATION HARNESS")
    out.append("Dataset: UCI 'Online Retail II'  |  Period: " + PERIOD)
    out.append(f"Tax rate: {rate:.0%}   Payment terms: {DEFAULT_BILLING.payment_terms_days} days   as_of: {AS_OF.isoformat()}")
    out.append(bar)
    out.append("")
    out.append(f"Customers invoiced : {len(rows)}")
    out.append(f"Total billed       : $ {total_billed:,.2f}")
    out.append(f"Overdue (as_of)    : {overdue_count}")
    out.extend(_skip_block(skips))
    out.append("")

    # per-customer table
    hdr = f"{'CUSTOMER':>9}  {'LINES':>5}  {'SUBTOTAL':>10}  {'TAX':>8}  {'TOTAL':>10}  {'RECON':>6}  {'REMIND':>8}"
    out.append(hdr)
    out.append("-" * len(hdr))
    for r in rows:
        recon = "PASS" if r["ok"] else "FAIL"
        rem = ",".join(str(x) for x in r["reminders"]) if r["reminders"] else "-"
        out.append(
            f"{r['client_id']:>9}  {r['lines']:>5}  "
            f"{r['subtotal']:>10,.2f}  {r['tax']:>8,.2f}  {r['total']:>10,.2f}  "
            f"{recon:>6}  {rem:>8}"
        )
        if not r["ok"]:
            out.append(f"            -> {r['detail']}")
    out.append("")

    verdict = "PASS" if (all_pass and rows) else "FAIL"
    out.append(bar)
    out.append(f"RECONCILIATION (engine vs independent recompute, within $0.01): {verdict}")
    out.append(bar)
    out.append("")
    return "\n".join(out) + "\n"


def render_md(rows, skips, all_pass, overdue_count, total_billed, rate) -> str:
    verdict = "PASS" if (all_pass and rows) else "FAIL"
    md: List[str] = []
    md.append("# Blueprint 03 - Invoicing & Billing: Real-Data Validation Report")
    md.append("")
    md.append("- **Dataset:** UCI Machine Learning Repository - *Online Retail II*")
    md.append(f"- **Period:** {PERIOD}")
    md.append(f"- **Tax rate:** {rate:.0%}  |  **Payment terms:** {DEFAULT_BILLING.payment_terms_days} days  |  **as_of:** {AS_OF.isoformat()}")
    md.append(f"- **Customers invoiced:** {len(rows)}")
    md.append(f"- **Total billed:** $ {total_billed:,.2f}")
    md.append(f"- **Overdue (as_of):** {overdue_count}")
    md.append(f"- **Reconciliation (engine vs independent recompute, within $0.01):** **{verdict}**")
    md.append("")
    md.append("## Rows skipped (logged, never silent)")
    md.append("")
    md.append(f"Total skipped: **{skips.total}**")
    md.append("")
    md.append("| Reason | Count |")
    md.append("|---|---|")
    for reason, n in skips.as_rows():
        md.append(f"| {reason} | {n} |")
    md.append("")
    md.append("## Per-customer reconciliation")
    md.append("")
    md.append("| Customer | Lines | Subtotal | Tax | Total | Engine vs Recompute | Reminders fired |")
    md.append("|---|---|---|---|---|---|---|")
    for r in rows:
        recon = "PASS" if r["ok"] else f"FAIL ({r['detail']})"
        rem = ", ".join(str(x) for x in r["reminders"]) if r["reminders"] else "-"
        md.append(
            f"| {r['client_id']} | {r['lines']} | $ {r['subtotal']:,.2f} | "
            f"$ {r['tax']:,.2f} | $ {r['total']:,.2f} | {recon} | {rem} |"
        )
    md.append("")
    md.append("## How it works")
    md.append("")
    md.append("1. Real Online Retail II rows are ingested and shaped into the blueprint's "
              "`UsageRecord` (adapter.py). Returns, missing Customer IDs and blank/zero prices "
              "are dropped and counted by reason.")
    md.append("2. One invoice per customer is built by the blueprint engine "
              "(`src.invoicing.build_invoice`) - that code is reused, not reimplemented.")
    md.append("3. An **independent** recomputation (`subtotal = sum(qty*price)`, "
              "`tax = subtotal*rate`, `total = subtotal+tax`) cross-checks the engine within $0.01.")
    md.append("4. The blueprint reminder engine (`src.reminders`) determines overdue invoices "
              f"and which escalation offsets {DEFAULT_BILLING.reminder_offsets_days} have fired by `as_of`.")
    md.append("")
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    raise SystemExit(run())
