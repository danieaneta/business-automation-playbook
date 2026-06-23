"""Payment reminders.

Given an unpaid invoice and a fixed ``as_of`` date, decide which escalating reminder offsets
should have fired. Deterministic: it never reads the wall clock — the caller passes ``as_of``.
"""

from __future__ import annotations

from datetime import date
from typing import List

from .config import DEFAULT_BILLING, BillingConfig
from .models import Invoice


def is_overdue(invoice: Invoice, as_of: date) -> bool:
    """True if the invoice is unpaid and past its due date as of ``as_of``."""
    return invoice.balance_due > 0 and as_of > invoice.due_date


def due_reminders(
    invoice: Invoice, as_of: date, config: BillingConfig = DEFAULT_BILLING
) -> List[int]:
    """Return the reminder offsets (days past due) that should have fired by ``as_of``.

    A reminder at offset ``n`` fires once the invoice is unpaid and at least ``n`` days past its
    due date. Returns an empty list for paid invoices or before the due date. The list is sorted
    ascending so the largest value is the most recent reminder.
    """
    if invoice.balance_due <= 0:
        return []
    days_past = invoice.days_overdue(as_of)
    if days_past <= 0:
        return []
    return sorted(offset for offset in config.reminder_offsets_days if days_past >= offset)


def next_reminder(
    invoice: Invoice, as_of: date, config: BillingConfig = DEFAULT_BILLING
) -> int | None:
    """The single reminder offset to send *now* (the most recent one due), or None."""
    fired = due_reminders(invoice, as_of, config)
    return fired[-1] if fired else None
