"""Invoice building.

Aggregates a client's usage records for a billing period into a single invoice with computed
subtotal, tax, total, and due date. Pure and deterministic so the math is fully testable; money
is rounded to 2 decimal places at every boundary.
"""

from __future__ import annotations

from datetime import date
from typing import List

from .config import DEFAULT_BILLING, BillingConfig
from .models import Invoice, UsageRecord


def _money(value: float) -> float:
    """Round to 2 decimal places (cents)."""
    return round(value + 0.0, 2)


def invoice_id(client_id: str, period: str) -> str:
    """Deterministic invoice id, also the idempotency key: one invoice per client+period."""
    return f"INV-{client_id}-{period}"


def period_end(period: str) -> date:
    """Last day of a ``YYYY-MM`` billing period."""
    year_s, month_s = period.split("-")
    year, month = int(year_s), int(month_s)
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    from datetime import timedelta

    return next_month_first - timedelta(days=1)


def build_invoice(
    client_id: str,
    usage_records: List[UsageRecord],
    period: str,
    config: BillingConfig = DEFAULT_BILLING,
) -> Invoice:
    """Build an :class:`Invoice` from a client's usage in a period.

    subtotal = sum(line amounts); tax = subtotal * tax_rate; total = subtotal + tax.
    due_date = period end + payment_terms_days. All money rounded to 2dp.
    """
    line_items = []
    subtotal = 0.0
    for rec in usage_records:
        if rec.client_id != client_id:
            raise ValueError(
                f"usage record for {rec.client_id!r} passed to invoice for {client_id!r}"
            )
        amount = rec.amount
        subtotal += amount
        line_items.append(
            {
                "description": rec.description,
                "qty": rec.qty,
                "unit_price": rec.unit_price,
                "amount": amount,
                "date": rec.date.isoformat(),
            }
        )

    subtotal = _money(subtotal)
    tax = _money(subtotal * config.tax_rate)
    total = _money(subtotal + tax)
    due = config.due_date_from(period_end(period))

    return Invoice(
        id=invoice_id(client_id, period),
        client_id=client_id,
        period=period,
        line_items=line_items,
        subtotal=subtotal,
        tax=tax,
        total=total,
        due_date=due,
        currency=config.currency,
        status="open",
        amount_paid=0.0,
    )
