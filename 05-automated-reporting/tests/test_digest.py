from src.config import DEFAULT_REPORT
from src.digest import render_digest
from src.models import MetricSnapshot, Report
from src.transform import compare


def _report():
    cur = [
        MetricSnapshot("crm", "new_leads", 138, "2026-W24"),
        MetricSnapshot("billing", "churned_customers", 5, "2026-W24"),
        MetricSnapshot("analytics", "signups", 31, "2026-W24"),
    ]
    prev = [
        MetricSnapshot("crm", "new_leads", 120, "2026-W23"),
        MetricSnapshot("billing", "churned_customers", 2, "2026-W23"),
        MetricSnapshot("analytics", "signups", 0, "2026-W23"),
    ]
    rows = compare(cur, prev, DEFAULT_REPORT)
    return Report("2026-W24", "2026-W23", "Acme Inc", rows)


def test_digest_is_ascii_only():
    digest = render_digest(_report())
    # Encoding to ASCII must not raise — guards against stray Unicode arrows/emoji.
    digest.encode("ascii")


def test_digest_contains_period_and_key_numbers():
    digest = render_digest(_report())
    assert "2026-W24" in digest
    assert "2026-W23" in digest
    assert "New Leads" in digest
    assert "138" in digest  # current value present


def test_digest_marks_big_movers():
    digest = render_digest(_report())
    # churned 2 -> 5 (+150%) and new_leads +15% are big movers; signups is 'new'.
    assert "Highlights (big movers)" in digest
    assert "*" in digest  # highlight marker present
    assert "new" in digest  # previous-zero metric rendered as 'new'


def test_digest_shows_direction_words_not_arrows():
    digest = render_digest(_report())
    assert "up vs prior" in digest


def test_digest_no_highlights_omits_highlight_section():
    cur = [MetricSnapshot("crm", "new_leads", 101, "P")]
    prev = [MetricSnapshot("crm", "new_leads", 100, "P")]
    report = Report("P", "P0", "Acme", compare(cur, prev, DEFAULT_REPORT))
    digest = render_digest(report)
    assert "Highlights (big movers)" not in digest
    assert "All metrics" in digest
