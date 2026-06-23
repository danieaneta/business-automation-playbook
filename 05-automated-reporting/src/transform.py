"""Metric comparison.

Turns current + prior period snapshots into report rows: delta, percent change, direction, and
a highlight flag for big movers. Pure functions so the math is deterministic and testable — no
clocks, no I/O.
"""

from __future__ import annotations

from typing import Dict, List

from .config import DEFAULT_REPORT, ReportConfig
from .models import MetricSnapshot, ReportRow


def _direction(delta: float) -> str:
    if delta > 0:
        return "up"
    if delta < 0:
        return "down"
    return "flat"


def _pct_change(value: float, previous: float) -> float | None:
    """Percent change from ``previous`` to ``value``.

    Returns None when there is no prior value to divide by (previous == 0); the caller renders
    that as 'new' rather than a misleading infinity. If both are zero, change is 0%.
    """
    if previous == 0:
        return 0.0 if value == 0 else None
    return (value - previous) / abs(previous) * 100.0


def _index(snapshots: List[MetricSnapshot]) -> Dict[str, float]:
    return {f"{s.source}.{s.metric}": s.value for s in snapshots}


def compare(
    current: List[MetricSnapshot],
    previous: List[MetricSnapshot],
    config: ReportConfig = DEFAULT_REPORT,
) -> List[ReportRow]:
    """Compare current vs previous snapshots into ordered report rows.

    Rows follow the order of ``config.metrics`` so the digest is stable across runs. A metric
    missing from current is skipped; a metric missing from previous is treated as previous=0.
    """
    cur = _index(current)
    prev = _index(previous)

    rows: List[ReportRow] = []
    for m in config.metrics:
        key = f"{m.source}.{m.metric}"
        if key not in cur:
            continue
        value = cur[key]
        previous_value = prev.get(key, 0.0)
        delta = value - previous_value
        pct = _pct_change(value, previous_value)
        rows.append(
            ReportRow(
                source=m.source,
                metric=m.metric,
                display_name=m.display_name,
                value=value,
                previous=previous_value,
                delta=delta,
                pct_change=pct,
                direction=_direction(delta),
                highlighted=config.is_highlight(pct),
            )
        )
    return rows
