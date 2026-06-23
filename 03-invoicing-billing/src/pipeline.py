"""Invoicing & billing pipeline orchestrator.

The end-to-end flow that the n8n workflow mirrors visually:

    period ends  ->  aggregate usage by client  ->  build invoice  ->  store (idempotent)
                 ->  apply any payments  ->  compute due reminders as of a fixed date

Every step emits a structured log line, so a billing run is fully auditable. All "today"
logic takes an explicit ``as_of`` date so runs are deterministic and testable.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List

from shared.logging_config import get_logger

from .config import DEFAULT_BILLING, BillingConfig
from .invoicing import build_invoice
from .ledger import InvoiceLedger
from .models import Invoice, Payment, UsageRecord
from .reconcile import apply_payment
from .reminders import due_reminders, is_overdue

logger = get_logger("invoicing_pipeline")

# Paths relative to the blueprint folder (this file lives in <blueprint>/src/).
BLUEPRINT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_USAGE = BLUEPRINT_DIR / "data" / "sample_usage.json"
DEFAULT_PAYMENTS = BLUEPRINT_DIR / "data" / "sample_payments.json"
DEFAULT_STORE = BLUEPRINT_DIR / "data" / "invoices_store.json"

# Fixed "today" for the demo so output is deterministic (sample period is 2026-04).
# Period 2026-04 ends 2026-04-30; net-30 due date is 2026-05-30; as-of 2026-06-15 is 16 days
# overdue, so all reminder offsets ([3, 7, 14]) have fired for any still-unpaid invoice.
DEFAULT_AS_OF = date(2026, 6, 15)
DEFAULT_PERIOD = "2026-04"


def aggregate_usage(records: Iterable[UsageRecord], period: str) -> Dict[str, List[UsageRecord]]:
    """Group usage records by client_id for the given period (one bucket per client)."""
    by_client: Dict[str, List[UsageRecord]] = {}
    for rec in records:
        by_client.setdefault(rec.client_id, []).append(rec)
    return by_client


def run_pipeline(
    raw_usage: Iterable[Dict[str, Any]],
    period: str = DEFAULT_PERIOD,
    as_of: date = DEFAULT_AS_OF,
    raw_payments: Iterable[Dict[str, Any]] | None = None,
    store_path: str | Path = DEFAULT_STORE,
    config: BillingConfig = DEFAULT_BILLING,
) -> List[Invoice]:
    """Aggregate usage -> build+store invoices idempotently -> reconcile -> tag reminders.

    Returns the in-memory invoices (with payments applied) for the period.
    """
    ledger = InvoiceLedger(store_path)
    records = [UsageRecord.from_dict(r) for r in raw_usage]
    payments = [Payment.from_dict(p) for p in (raw_payments or [])]
    payments_by_invoice: Dict[str, List[Payment]] = {}
    for pmt in payments:
        payments_by_invoice.setdefault(pmt.invoice_id, []).append(pmt)

    invoices: List[Invoice] = []
    for client_id, client_records in aggregate_usage(records, period).items():
        invoice = build_invoice(client_id, client_records, period, config)
        created = ledger.record_invoice(invoice)

        for pmt in payments_by_invoice.get(invoice.id, []):
            apply_payment(invoice, pmt)
        # Persist the reconciled state so the ledger reflects payments too.
        ledger.record_invoice(invoice)

        fired = due_reminders(invoice, as_of, config)
        logger.info(
            "invoice processed",
            extra={"context": {
                "invoice_id": invoice.id, "client_id": client_id, "period": period,
                "total": invoice.total, "status": invoice.status,
                "balance_due": invoice.balance_due, "created": created,
                "reminders_due": fired, "overdue": is_overdue(invoice, as_of),
            }},
        )
        invoices.append(invoice)

    logger.info(
        "billing run complete",
        extra={"context": {
            "period": period, "invoices": len(invoices), "ledger_total": ledger.count(),
        }},
    )
    return invoices


def main(
    usage_path: str | Path = DEFAULT_USAGE,
    payments_path: str | Path = DEFAULT_PAYMENTS,
    store_path: str | Path = DEFAULT_STORE,
    period: str = DEFAULT_PERIOD,
    as_of: date = DEFAULT_AS_OF,
) -> None:
    raw_usage = json.loads(Path(usage_path).read_text(encoding="utf-8"))
    raw_payments = []
    if Path(payments_path).exists():
        raw_payments = json.loads(Path(payments_path).read_text(encoding="utf-8"))

    invoices = run_pipeline(
        raw_usage, period=period, as_of=as_of, raw_payments=raw_payments, store_path=store_path
    )

    total_billed = round(sum(inv.total for inv in invoices), 2)
    reminders_due = sum(1 for inv in invoices if due_reminders(inv, as_of))
    overdue = sum(1 for inv in invoices if is_overdue(inv, as_of))
    currency = invoices[0].currency if invoices else DEFAULT_BILLING.currency

    print("\n=== Invoicing & Billing run summary ===")
    print(f"Period: {period}   as of {as_of.isoformat()}")
    print(f"Invoices created: {len(invoices)}")
    print(f"Total billed: {total_billed:.2f} {currency}")
    print(f"Reminders due: {reminders_due}    Overdue invoices: {overdue}")
    print("\nInvoices:")
    for inv in sorted(invoices, key=lambda i: i.total, reverse=True):
        fired = due_reminders(inv, as_of)
        tag = f"reminder@{fired[-1]}d" if fired else ("paid" if inv.status == "paid" else "on time")
        print(
            f"  {inv.id:<22} {inv.total:>9.2f} {inv.currency}  "
            f"due {inv.due_date.isoformat()}  {inv.status:<7} -> {tag}"
        )
    print(f"\nInvoice ledger written to: {store_path}")


if __name__ == "__main__":
    main()
