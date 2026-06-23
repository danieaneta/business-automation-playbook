from src.config import DEFAULT_REPORT, ReportConfig
from src.models import MetricSnapshot
from src.transform import compare


def _snap(source, metric, value, period="P"):
    return MetricSnapshot(source=source, metric=metric, value=value, period=period)


def _row(rows, metric):
    return next(r for r in rows if r.metric == metric)


def test_delta_and_pct_change_math():
    cur = [_snap("crm", "new_leads", 138)]
    prev = [_snap("crm", "new_leads", 120)]
    row = _row(compare(cur, prev), "new_leads")
    assert row.delta == 18
    assert round(row.pct_change, 1) == 15.0
    assert row.direction == "up"


def test_negative_change_is_down():
    cur = [_snap("crm", "new_leads", 90)]
    prev = [_snap("crm", "new_leads", 120)]
    row = _row(compare(cur, prev), "new_leads")
    assert row.delta == -30
    assert row.pct_change < 0
    assert row.direction == "down"


def test_no_change_is_flat():
    cur = [_snap("crm", "new_leads", 100)]
    prev = [_snap("crm", "new_leads", 100)]
    row = _row(compare(cur, prev), "new_leads")
    assert row.delta == 0
    assert row.pct_change == 0.0
    assert row.direction == "flat"


def test_previous_zero_yields_none_pct_not_crash():
    """Previous value of 0 must not divide-by-zero; pct_change is None (rendered as 'new')."""
    cur = [_snap("analytics", "signups", 31)]
    prev = [_snap("analytics", "signups", 0)]
    row = _row(compare(cur, prev), "signups")
    assert row.pct_change is None
    assert row.direction == "up"
    assert row.highlighted is False  # None pct never highlights


def test_both_zero_is_flat_zero_pct():
    cur = [_snap("analytics", "signups", 0)]
    prev = [_snap("analytics", "signups", 0)]
    row = _row(compare(cur, prev), "signups")
    assert row.pct_change == 0.0
    assert row.direction == "flat"


def test_missing_previous_treated_as_zero():
    cur = [_snap("crm", "new_leads", 50)]
    row = _row(compare(cur, []), "new_leads")
    assert row.previous == 0.0


def test_highlight_threshold_just_under_vs_just_over():
    cfg = ReportConfig(highlight_threshold_pct=10.0)
    # 100 -> 109 is +9% : under threshold, not highlighted
    under = _row(compare([_snap("crm", "new_leads", 109)], [_snap("crm", "new_leads", 100)], cfg), "new_leads")
    # 100 -> 110 is +10% : at threshold, highlighted
    over = _row(compare([_snap("crm", "new_leads", 110)], [_snap("crm", "new_leads", 100)], cfg), "new_leads")
    assert under.highlighted is False
    assert over.highlighted is True


def test_rows_follow_config_order_and_skip_unknown():
    # Only provide two of the configured metrics, out of order; output follows config order.
    cur = [_snap("billing", "mrr", 49100), _snap("crm", "new_leads", 138)]
    prev = [_snap("billing", "mrr", 48200), _snap("crm", "new_leads", 120)]
    rows = compare(cur, prev, DEFAULT_REPORT)
    metrics = [r.metric for r in rows]
    assert metrics == ["new_leads", "mrr"]  # config lists new_leads before mrr
