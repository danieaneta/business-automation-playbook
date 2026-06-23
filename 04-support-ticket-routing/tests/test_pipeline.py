import json
from pathlib import Path

from src.pipeline import run_pipeline
from src.routing import is_breaching

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_tickets.json"
AS_OF = "2026-06-23T12:00:00+00:00"


def _raw_tickets():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def test_skips_tickets_without_id_or_timestamp(tmp_path):
    results = run_pipeline(_raw_tickets(), store_path=tmp_path / "tickets.json")
    ids = {r.ticket.id for r in results}
    assert "" not in ids


def test_idempotent_store_writes(tmp_path):
    """The sample data contains T-1001 twice; the store must hold ONE record for it."""
    store = tmp_path / "tickets.json"
    run_pipeline(_raw_tickets(), store_path=store)
    records = json.loads(store.read_text(encoding="utf-8"))
    assert "T-1001" in records
    # Six valid rows, one malformed skipped, one duplicate collapsed -> 5 unique records.
    assert len(records) == 5


def test_rerun_does_not_duplicate(tmp_path):
    store = tmp_path / "tickets.json"
    run_pipeline(_raw_tickets(), store_path=store)
    count_after_first = len(json.loads(store.read_text(encoding="utf-8")))
    run_pipeline(_raw_tickets(), store_path=store)
    count_after_second = len(json.loads(store.read_text(encoding="utf-8")))
    assert count_after_first == count_after_second == 5


def test_duplicate_updates_single_record(tmp_path):
    """The second T-1001 row is an updated body; the stored subject must reflect the last write."""
    store = tmp_path / "tickets.json"
    run_pipeline(_raw_tickets(), store_path=store)
    records = json.loads(store.read_text(encoding="utf-8"))
    assert records["T-1001"]["subject"] == "URGENT: production is down (update)"


def test_outage_escalates_and_breaches(tmp_path):
    results = run_pipeline(_raw_tickets(), store_path=tmp_path / "tickets.json")
    outage = next(r for r in results if r.ticket.id == "T-1001")
    assert outage.priority == "high"
    assert outage.escalate is True
    assert is_breaching(outage, as_of=AS_OF) is True


def test_breach_count_is_deterministic(tmp_path):
    results = run_pipeline(_raw_tickets(), store_path=tmp_path / "tickets.json")
    breaching = [r for r in results if is_breaching(r, as_of=AS_OF)]
    # T-1001 (high, due 11:30) and T-1003 (low, received 06-20, due 06-21) are past 12:00 on 06-23.
    breach_ids = {r.ticket.id for r in breaching}
    assert breach_ids == {"T-1001", "T-1003"}
