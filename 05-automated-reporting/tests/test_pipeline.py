import json
from pathlib import Path

from src.pipeline import (
    DEFAULT_PERIOD,
    DEFAULT_PREVIOUS_PERIOD,
    build_report,
    run_pipeline,
)

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_metrics.json"


def test_build_report_pulls_all_sources():
    report = build_report(metrics_file=SAMPLE)
    sources = {r.source for r in report.rows}
    assert sources == {"crm", "billing", "analytics"}
    assert report.period == DEFAULT_PERIOD
    assert report.previous_period == DEFAULT_PREVIOUS_PERIOD


def test_sample_has_expected_big_movers():
    report = build_report(metrics_file=SAMPLE)
    highlighted = {r.metric for r in report.highlights}
    # new_leads (+15%), new_customers (+55%), churned_customers (+150%) clear 10%.
    assert "new_leads" in highlighted
    assert "churned_customers" in highlighted
    # signups went 0 -> 31 (pct undefined): must NOT be a highlight.
    assert "signups" not in highlighted


def test_first_run_delivers(tmp_path):
    store = tmp_path / "delivery.json"
    summary = run_pipeline(metrics_file=SAMPLE, store_path=store)
    assert summary["delivery"].status == "delivered"
    assert summary["delivery"].delivered is True


def test_second_run_same_period_is_skipped(tmp_path):
    """Idempotency: delivering the same period twice must NOT re-deliver."""
    store = tmp_path / "delivery.json"
    run_pipeline(metrics_file=SAMPLE, store_path=store)
    second = run_pipeline(metrics_file=SAMPLE, store_path=store)
    assert second["delivery"].status == "skipped"
    # The store holds exactly one delivery record, keyed by period.
    records = json.loads(store.read_text(encoding="utf-8"))
    assert list(records.keys()) == [DEFAULT_PERIOD]


def test_different_period_delivers_again(tmp_path):
    store = tmp_path / "delivery.json"
    run_pipeline(metrics_file=SAMPLE, store_path=store)
    # A new period (using the same data file, swapping the labels) delivers fresh.
    other = run_pipeline(
        period="2026-W23",
        previous_period="2026-W23",
        metrics_file=SAMPLE,
        store_path=store,
    )
    assert other["delivery"].status == "delivered"
    records = json.loads(store.read_text(encoding="utf-8"))
    assert set(records.keys()) == {DEFAULT_PERIOD, "2026-W23"}


def test_summary_counts_match_report(tmp_path):
    summary = run_pipeline(metrics_file=SAMPLE, store_path=tmp_path / "d.json")
    report = summary["report"]
    assert summary["metrics_reported"] == len(report.rows)
    assert summary["highlights"] == len(report.highlights)
