"""Source connectors.

Each connector fetches the metrics for one source in one period. In production a connector
calls a real API (HubSpot/Salesforce for CRM, Stripe/Chargebee for billing, GA4/Plausible for
analytics) behind the shared retry wrapper. For a runnable, key-free demo it reads
`data/sample_metrics.json`, which holds values per source/metric for the current AND prior
period. The `fetch_metrics(source, period)` signature is exactly what a real provider call
would look like, so swapping in HTTP is a one-function change.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from shared.retry import retry

from .models import MetricSnapshot

# Paths relative to the blueprint folder (this file lives in <blueprint>/src/).
BLUEPRINT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_METRICS_FILE = BLUEPRINT_DIR / "data" / "sample_metrics.json"


class MetricSource:
    """Reads metric snapshots from the bundled sample file.

    Swap-in: give each source its own subclass whose `_read` body calls the real API and
    returns a {metric: value} dict for the requested period. The retry wrapper and the rest of
    the pipeline stay unchanged.
    """

    def __init__(self, metrics_file: str | Path = DEFAULT_METRICS_FILE):
        self.metrics_file = Path(metrics_file)
        self._data: Dict[str, Any] = json.loads(
            self.metrics_file.read_text(encoding="utf-8")
        )

    @retry(attempts=3, base_delay=0.2, exceptions=(ConnectionError, TimeoutError))
    def fetch_metrics(self, source: str, period: str) -> List[MetricSnapshot]:
        """Return the metric snapshots for ``source`` in ``period``.

        The @retry wrapper is what a real network call needs; here it's a no-op safety net that
        also documents the production failure mode (transient connection/timeout errors).
        """
        values = self._read(source, period)
        return [
            MetricSnapshot.from_dict(source, period, metric, value)
            for metric, value in values.items()
        ]

    def _read(self, source: str, period: str) -> Dict[str, Any]:
        # Swap this single method for the real API call (GET metrics for the period).
        source_block = self._data.get(source)
        if source_block is None:
            raise KeyError(f"unknown source '{source}' in {self.metrics_file.name}")
        period_block = source_block.get(period)
        if period_block is None:
            raise KeyError(f"no data for source '{source}' period '{period}'")
        return dict(period_block)
