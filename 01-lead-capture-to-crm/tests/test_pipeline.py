import json
from pathlib import Path

from src.pipeline import run_pipeline

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_leads.json"


def _raw_leads():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def test_skips_leads_without_valid_email(tmp_path):
    results = run_pipeline(_raw_leads(), store_path=tmp_path / "crm.json")
    # The "not-an-email" record has no '@', so Lead.from_dict keeps it but pipeline must skip it.
    emails = {r.lead.email for r in results}
    assert "not-an-email" not in emails


def test_idempotent_crm_writes(tmp_path):
    """The sample data contains the same lead twice; the CRM must hold ONE record for it."""
    store = tmp_path / "crm.json"
    run_pipeline(_raw_leads(), store_path=store)
    records = json.loads(store.read_text(encoding="utf-8"))
    assert "priya@globalsystems.com" in records
    # Six raw rows, one invalid email skipped, one duplicate collapsed → 4 unique CRM records.
    assert len(records) == 4


def test_rerun_does_not_duplicate(tmp_path):
    store = tmp_path / "crm.json"
    run_pipeline(_raw_leads(), store_path=store)
    count_after_first = len(json.loads(store.read_text(encoding="utf-8")))
    run_pipeline(_raw_leads(), store_path=store)
    count_after_second = len(json.loads(store.read_text(encoding="utf-8")))
    assert count_after_first == count_after_second


def test_hot_lead_routed_to_sales(tmp_path):
    results = run_pipeline(_raw_leads(), store_path=tmp_path / "crm.json")
    priya = next(r for r in results if r.lead.email == "priya@globalsystems.com")
    assert priya.tier == "hot"
    assert priya.next_action == "notify_sales_immediately"
