from datetime import date

from src.invoicing import build_invoice
from src.models import Payment, UsageRecord
from src.reconcile import apply_payment


def _invoice(total_price=1000.00):
    records = [UsageRecord("acme", "Sub", 1, total_price, date(2026, 4, 1))]
    return build_invoice("acme", records, "2026-04")


def test_full_payment_marks_paid():
    inv = _invoice()
    pmt = Payment("acme", inv.id, inv.total, date(2026, 5, 20))
    apply_payment(inv, pmt)
    assert inv.status == "paid"
    assert inv.balance_due == 0.0


def test_partial_payment_marks_partial():
    inv = _invoice()
    pmt = Payment("acme", inv.id, 400.00, date(2026, 5, 20))
    apply_payment(inv, pmt)
    assert inv.status == "partial"
    assert inv.balance_due == round(inv.total - 400.00, 2)


def test_instalments_accumulate_to_paid():
    inv = _invoice()
    apply_payment(inv, Payment("acme", inv.id, 600.00, date(2026, 5, 20)))
    assert inv.status == "partial"
    apply_payment(inv, Payment("acme", inv.id, inv.total - 600.00, date(2026, 5, 25)))
    assert inv.status == "paid"
    assert inv.balance_due == 0.0


def test_overpayment_still_paid_no_negative_balance_status():
    inv = _invoice()
    apply_payment(inv, Payment("acme", inv.id, inv.total + 50.0, date(2026, 5, 20)))
    assert inv.status == "paid"


def test_payment_for_wrong_invoice_rejected():
    inv = _invoice()
    pmt = Payment("acme", "INV-globex-2026-04", 100.0, date(2026, 5, 20))
    try:
        apply_payment(inv, pmt)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_nonpositive_payment_rejected():
    inv = _invoice()
    try:
        apply_payment(inv, Payment("acme", inv.id, 0.0, date(2026, 5, 20)))
        assert False, "expected ValueError"
    except ValueError:
        pass
