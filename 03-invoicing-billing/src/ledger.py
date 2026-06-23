"""Invoice ledger.

A thin, idempotent client that writes invoices to a "billing system". The demo backs it with
the shared JsonStore (a local file); a real one swaps the `_write` body for a Stripe/QuickBooks
API call wrapped in the same retry decorator.

Idempotency: invoices are keyed by ``client_id:period``, so re-running a billing period updates
the one invoice instead of creating a duplicate — the single most common bug in hand-rolled
billing automations (double-billing a client).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from shared.retry import retry
from shared.store import JsonStore

from .models import Invoice


def ledger_key(client_id: str, period: str) -> str:
    """The idempotency key for an invoice: one per client per billing period."""
    return f"{client_id}:{period}"


class InvoiceLedger:
    """Idempotent upsert interface to the billing system."""

    def __init__(self, store_path: str | Path):
        self._store = JsonStore(store_path)

    @retry(attempts=3, base_delay=0.2, exceptions=(ConnectionError, TimeoutError))
    def record_invoice(self, invoice: Invoice) -> bool:
        """Upsert an invoice keyed by client+period. Returns True if newly created.

        The @retry wrapper is what a real network call needs; here it's a no-op safety net that
        also documents the production failure mode (transient connection/timeout errors).
        """
        if not invoice.client_id or not invoice.period:
            raise ValueError("invoice is missing required 'client_id' or 'period'")
        return self._write(ledger_key(invoice.client_id, invoice.period), invoice.to_record())

    def _write(self, key: str, record: Dict[str, Any]) -> bool:
        # Swap this single method for the real API call (POST/PATCH by external id).
        return self._store.upsert(key, record)

    def get_invoice(self, client_id: str, period: str) -> Dict[str, Any] | None:
        return self._store.get(ledger_key(client_id, period))

    def count(self) -> int:
        return len(self._store)
