"""Payment reconciliation.

Applies a payment to an invoice and updates its status: ``paid`` when the balance is cleared,
``partial`` when some (but not all) is paid, ``open`` otherwise. Money is rounded to 2dp so
floating-point dust never leaves a cent owing.
"""

from __future__ import annotations

from .models import Invoice, Payment


def apply_payment(invoice: Invoice, payment: Payment) -> Invoice:
    """Apply ``payment`` to ``invoice`` (mutates and returns it).

    Accumulates onto ``amount_paid`` (a client may pay in instalments) and recomputes status:
    ``paid`` if the running total covers the invoice total, else ``partial``.
    """
    if payment.invoice_id and payment.invoice_id != invoice.id:
        raise ValueError(
            f"payment for invoice {payment.invoice_id!r} applied to {invoice.id!r}"
        )
    if payment.amount <= 0:
        raise ValueError("payment amount must be positive")

    invoice.amount_paid = round(invoice.amount_paid + payment.amount, 2)
    if invoice.amount_paid >= invoice.total:
        invoice.status = "paid"
    else:
        invoice.status = "partial"
    return invoice
