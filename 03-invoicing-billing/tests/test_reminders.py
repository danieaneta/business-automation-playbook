from datetime import date

from src.config import BillingConfig
from src.invoicing import build_invoice
from src.models import UsageRecord
from src.reminders import due_reminders, is_overdue, next_reminder

CFG = BillingConfig(reminder_offsets_days=[3, 7, 14], payment_terms_days=30)


def _invoice():
    # period 2026-04 -> due 2026-05-30
    records = [UsageRecord("acme", "Sub", 1, 1000.00, date(2026, 4, 1))]
    return build_invoice("acme", records, "2026-04", CFG)


def test_no_reminders_before_due_date():
    inv = _invoice()
    assert due_reminders(inv, date(2026, 5, 30), CFG) == []
    assert is_overdue(inv, date(2026, 5, 30)) is False


def test_no_reminder_one_day_past_due_below_first_offset():
    inv = _invoice()
    # 2 days overdue, first offset is 3
    assert due_reminders(inv, date(2026, 6, 1), CFG) == []


def test_first_reminder_fires_at_offset_three():
    inv = _invoice()
    # due 2026-05-30 + 3 = 2026-06-02
    assert due_reminders(inv, date(2026, 6, 2), CFG) == [3]
    assert next_reminder(inv, date(2026, 6, 2), CFG) == 3


def test_two_reminders_fired_by_offset_seven():
    inv = _invoice()
    assert due_reminders(inv, date(2026, 6, 6), CFG) == [3, 7]
    assert next_reminder(inv, date(2026, 6, 6), CFG) == 7


def test_all_reminders_fired_well_past_due():
    inv = _invoice()
    assert due_reminders(inv, date(2026, 6, 15), CFG) == [3, 7, 14]
    assert next_reminder(inv, date(2026, 6, 15), CFG) == 14


def test_paid_invoice_fires_no_reminders():
    inv = _invoice()
    inv.amount_paid = inv.total
    inv.status = "paid"
    assert due_reminders(inv, date(2026, 7, 1), CFG) == []
    assert is_overdue(inv, date(2026, 7, 1)) is False


def test_partial_invoice_still_overdue():
    inv = _invoice()
    inv.amount_paid = inv.total / 2
    inv.status = "partial"
    assert is_overdue(inv, date(2026, 6, 15)) is True
    assert due_reminders(inv, date(2026, 6, 15), CFG) == [3, 7, 14]
