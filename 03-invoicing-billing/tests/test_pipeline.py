import json
from datetime import date
from pathlib import Path

from src.pipeline import DEFAULT_AS_OF, DEFAULT_PERIOD, run_pipeline

DATA = Path(__file__).resolve().parent.parent / "data"
USAGE = DATA / "sample_usage.json"
PAYMENTS = DATA / "sample_payments.json"


def _raw_usage():
    return json.loads(USAGE.read_text(encoding="utf-8"))


def _raw_payments():
    return json.loads(PAYMENTS.read_text(encoding="utf-8"))


def test_one_invoice_per_client(tmp_path):
    invoices = run_pipeline(_raw_usage(), store_path=tmp_path / "inv.json")
    client_ids = sorted(inv.client_id for inv in invoices)
    assert client_ids == ["acme", "globex", "initech"]
    assert len(invoices) == 3


def test_invoices_stored_keyed_by_client_period(tmp_path):
    store = tmp_path / "inv.json"
    run_pipeline(_raw_usage(), store_path=store)
    records = json.loads(store.read_text(encoding="utf-8"))
    assert "acme:2026-04" in records
    assert "globex:2026-04" in records
    assert "initech:2026-04" in records


def test_rerun_same_period_does_not_duplicate(tmp_path):
    store = tmp_path / "inv.json"
    run_pipeline(_raw_usage(), store_path=store)
    count_first = len(json.loads(store.read_text(encoding="utf-8")))
    run_pipeline(_raw_usage(), store_path=store)
    count_second = len(json.loads(store.read_text(encoding="utf-8")))
    assert count_first == count_second == 3


def test_payments_reconciled_into_invoices(tmp_path):
    invoices = run_pipeline(
        _raw_usage(),
        raw_payments=_raw_payments(),
        store_path=tmp_path / "inv.json",
    )
    by_client = {inv.client_id: inv for inv in invoices}
    # globex paid in full -> paid; initech partial; acme unpaid -> open
    assert by_client["globex"].status == "paid"
    assert by_client["initech"].status == "partial"
    assert by_client["acme"].status == "open"


def test_reminders_fire_only_for_unpaid_overdue(tmp_path):
    from src.reminders import due_reminders

    invoices = run_pipeline(
        _raw_usage(),
        raw_payments=_raw_payments(),
        as_of=DEFAULT_AS_OF,
        store_path=tmp_path / "inv.json",
    )
    by_client = {inv.client_id: inv for inv in invoices}
    # as_of 2026-06-15 is 16 days past due -> all offsets for unpaid; none for the paid one
    assert due_reminders(by_client["acme"], DEFAULT_AS_OF) == [3, 7, 14]
    assert due_reminders(by_client["initech"], DEFAULT_AS_OF) == [3, 7, 14]
    assert due_reminders(by_client["globex"], DEFAULT_AS_OF) == []


def test_before_due_date_no_reminders(tmp_path):
    from src.reminders import due_reminders

    invoices = run_pipeline(
        _raw_usage(),
        as_of=date(2026, 5, 15),
        store_path=tmp_path / "inv.json",
    )
    for inv in invoices:
        assert due_reminders(inv, date(2026, 5, 15)) == []


def test_total_billed_matches_sum(tmp_path):
    invoices = run_pipeline(_raw_usage(), store_path=tmp_path / "inv.json")
    total = round(sum(inv.total for inv in invoices), 2)
    # acme 2116.80 + globex 1026.00 + initech 637.20
    assert total == 3780.00
