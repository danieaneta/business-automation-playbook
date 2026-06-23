from pathlib import Path

import pytest

from shared.retry import RetryError
from src.connectors import MetricSource

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_metrics.json"


def test_fetch_returns_snapshots_for_period():
    src = MetricSource(SAMPLE)
    snaps = src.fetch_metrics("crm", "2026-W24")
    by_metric = {s.metric: s.value for s in snaps}
    assert by_metric["new_leads"] == 138
    assert all(s.source == "crm" and s.period == "2026-W24" for s in snaps)


def test_unknown_source_raises_keyerror():
    src = MetricSource(SAMPLE)
    with pytest.raises(KeyError):
        src.fetch_metrics("nope", "2026-W24")


def test_unknown_period_raises_keyerror():
    src = MetricSource(SAMPLE)
    with pytest.raises(KeyError):
        src.fetch_metrics("crm", "1999-W01")


def test_fetch_is_retry_wrapped(monkeypatch):
    """A transient ConnectionError in the read path is retried, then succeeds."""
    src = MetricSource(SAMPLE)
    calls = {"n": 0}
    real_read = src._read

    def flaky_read(source, period):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return real_read(source, period)

    monkeypatch.setattr(src, "_read", flaky_read)
    snaps = src.fetch_metrics("crm", "2026-W24")
    assert calls["n"] == 3  # retried twice, succeeded on the third
    assert {s.metric for s in snaps} == {"new_leads", "qualified_leads"}


def test_fetch_gives_up_after_exhausting_retries(monkeypatch):
    src = MetricSource(SAMPLE)

    def always_fails(source, period):
        raise TimeoutError("down")

    monkeypatch.setattr(src, "_read", always_fails)
    with pytest.raises(RetryError):
        src.fetch_metrics("crm", "2026-W24")
