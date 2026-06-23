"""Billing configuration — tax, payment terms, reminder cadence, currency.

In a real deployment these live in environment variables / a config file so finance can tune
terms without touching code. See `.env.example` for the production-integration knobs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class BillingConfig:
    """Defines how invoices are priced, when they're due, and the reminder cadence."""

    # Sales tax / VAT applied to the subtotal (e.g. 0.08 = 8%).
    tax_rate: float = 0.08
    # Net terms: due date = period end + this many days.
    payment_terms_days: int = 30
    # Days *after* the due date at which a reminder should fire, escalating.
    reminder_offsets_days: List[int] = field(default_factory=lambda: [3, 7, 14])
    # ISO 4217 currency code, carried onto every invoice.
    currency: str = "USD"

    def due_date_from(self, period_end):
        """Return the due date for an invoice whose period ends on ``period_end``."""
        from datetime import timedelta

        return period_end + timedelta(days=self.payment_terms_days)


DEFAULT_BILLING = BillingConfig()
