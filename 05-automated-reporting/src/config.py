"""Report config: which sources to pull, how to label metrics, what counts as a big mover.

In a real deployment these live in environment variables / a config file so non-engineers can
tune the report (sources, display names, highlight threshold, delivery channel) without
touching code. See `.env.example` for the production-integration knobs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class MetricDef:
    """How one raw metric key is presented in the digest."""

    source: str
    metric: str
    display_name: str


@dataclass(frozen=True)
class ReportConfig:
    """Defines the report: its sources, metric definitions, and delivery rules."""

    # Metric definitions, in the order they appear in the digest.
    metrics: List[MetricDef] = field(
        default_factory=lambda: [
            MetricDef("crm", "new_leads", "New Leads"),
            MetricDef("crm", "qualified_leads", "Qualified Leads"),
            MetricDef("billing", "mrr", "MRR ($)"),
            MetricDef("billing", "new_customers", "New Customers"),
            MetricDef("billing", "churned_customers", "Churned Customers"),
            MetricDef("analytics", "website_visits", "Website Visits"),
            MetricDef("analytics", "signups", "Signups"),
        ]
    )

    # Flag a metric as a highlight when |pct change| >= this many percent.
    highlight_threshold_pct: float = 10.0

    # Where the digest gets delivered.
    channel: str = "#weekly-metrics"

    @property
    def sources(self) -> List[str]:
        """Distinct sources to fetch, in first-seen order."""
        seen: List[str] = []
        for m in self.metrics:
            if m.source not in seen:
                seen.append(m.source)
        return seen

    def metrics_for(self, source: str) -> List[MetricDef]:
        return [m for m in self.metrics if m.source == source]

    def is_highlight(self, pct_change: float | None) -> bool:
        """A metric is a highlight when its absolute pct change clears the threshold."""
        if pct_change is None:
            return False
        return abs(pct_change) >= self.highlight_threshold_pct

    def display_lookup(self) -> Dict[str, str]:
        """Map 'source.metric' -> display name."""
        return {f"{m.source}.{m.metric}": m.display_name for m in self.metrics}


DEFAULT_REPORT = ReportConfig()
