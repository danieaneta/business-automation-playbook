from datetime import date

from src.config import BillingConfig
from src.invoicing import build_invoice, invoice_id, period_end
from src.models import UsageRecord


def _usage(client_id="acme"):
    return [
        UsageRecord(client_id, "Subscription", 1, 1200.00, date(2026, 4, 1)),
        UsageRecord(client_id, "API calls (per 1k)", 320, 0.50, date(2026, 4, 28)),
        UsageRecord(client_id, "Support hours", 4, 150.00, date(2026, 4, 22)),
    ]


def test_subtotal_is_sum_of_line_amounts():
    inv = build_invoice("acme", _usage(), "2026-04")
    # 1200 + 160 + 600
    assert inv.subtotal == 1960.00
    assert len(inv.line_items) == 3


def test_tax_is_subtotal_times_rate():
    cfg = BillingConfig(tax_rate=0.08)
    inv = build_invoice("acme", _usage(), "2026-04", cfg)
    assert inv.tax == 156.80  # 1960 * 0.08


def test_total_is_subtotal_plus_tax():
    inv = build_invoice("acme", _usage(), "2026-04")
    assert inv.total == round(inv.subtotal + inv.tax, 2)
    assert inv.total == 2116.80


def test_money_is_rounded_to_two_places():
    records = [UsageRecord("x", "fractional", 3, 0.333, date(2026, 4, 1))]
    cfg = BillingConfig(tax_rate=0.10)
    inv = build_invoice("x", records, "2026-04", cfg)
    # 3 * 0.333 = 0.999 -> rounds to 1.00; tax 1.00 * 0.10 = 0.10; total 1.10
    assert inv.subtotal == 1.00
    assert inv.tax == 0.10
    assert inv.total == 1.10
    # Every money field is rounded to exactly 2 decimal places.
    for value in (inv.subtotal, inv.tax, inv.total):
        assert round(value, 2) == value


def test_zero_tax_rate():
    cfg = BillingConfig(tax_rate=0.0)
    inv = build_invoice("acme", _usage(), "2026-04", cfg)
    assert inv.tax == 0.0
    assert inv.total == inv.subtotal


def test_period_end_handles_month_and_year_rollover():
    assert period_end("2026-04") == date(2026, 4, 30)
    assert period_end("2026-02") == date(2026, 2, 28)
    assert period_end("2026-12") == date(2026, 12, 31)


def test_due_date_is_period_end_plus_terms():
    cfg = BillingConfig(payment_terms_days=30)
    inv = build_invoice("acme", _usage(), "2026-04", cfg)
    # 2026-04-30 + 30 days = 2026-05-30
    assert inv.due_date == date(2026, 5, 30)


def test_invoice_id_is_deterministic_idempotency_key():
    assert invoice_id("acme", "2026-04") == "INV-acme-2026-04"
    inv1 = build_invoice("acme", _usage(), "2026-04")
    inv2 = build_invoice("acme", _usage(), "2026-04")
    assert inv1.id == inv2.id


def test_mismatched_client_record_rejected():
    bad = [UsageRecord("globex", "x", 1, 10.0, date(2026, 4, 1))]
    try:
        build_invoice("acme", bad, "2026-04")
        assert False, "expected ValueError"
    except ValueError:
        pass
