import json
from pathlib import Path

from src.pipeline import run_pipeline

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_deals.json"


def _raw_deals():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def test_skips_deal_with_missing_id(tmp_path):
    results = run_pipeline(_raw_deals(), store_path=tmp_path / "store.json")
    deal_ids = {r.deal.deal_id for r in results}
    assert "" not in deal_ids
    # Five raw rows: one missing-id skipped, one duplicate of DEAL-1001 collapses by step keys.
    # The pipeline still processes the duplicate row, but it provisions nothing new (see below).
    assert "DEAL-1001" in deal_ids
    assert "DEAL-1003" in deal_ids


def test_enterprise_deal_onboarded_with_csm(tmp_path):
    results = run_pipeline(_raw_deals(), store_path=tmp_path / "store.json")
    ent = next(r for r in results if r.deal.deal_id == "DEAL-1003")
    assert "assign_csm" in ent.required_steps
    assert "assign_csm" in ent.completed
    assert ent.percent_complete == 100


def test_duplicate_deal_in_batch_provisions_nothing_new(tmp_path):
    """DEAL-1001 appears twice in the sample; the second occurrence must skip every step."""
    results = run_pipeline(_raw_deals(), store_path=tmp_path / "store.json")
    dupes = [r for r in results if r.deal.deal_id == "DEAL-1001"]
    assert len(dupes) == 2
    first, second = dupes
    assert first.completed and not first.skipped       # first run provisions
    assert not second.completed and second.skipped      # second run skips everything
    assert second.status == "already_onboarded"


def test_rerun_does_not_reprovision(tmp_path):
    store = tmp_path / "store.json"
    run_pipeline(_raw_deals(), store_path=store)
    steps_after_first = len(json.loads(store.read_text(encoding="utf-8")))
    second = run_pipeline(_raw_deals(), store_path=store)
    steps_after_second = len(json.loads(store.read_text(encoding="utf-8")))
    # No new step records on re-run.
    assert steps_after_first == steps_after_second
    # And every deal on the second run is fully skipped (nothing newly completed).
    assert all(not r.completed for r in second)
    assert all(r.skipped for r in second)


def test_store_keyed_by_deal_and_step(tmp_path):
    store = tmp_path / "store.json"
    run_pipeline(_raw_deals(), store_path=store)
    records = json.loads(store.read_text(encoding="utf-8"))
    # 5 base steps for DEAL-1001 + 5 for DEAL-1002 + 6 for DEAL-1003 (enterprise) = 16.
    assert len(records) == 16
    assert "DEAL-1003:assign_csm" in records
    assert "DEAL-1001:provision_account" in records
