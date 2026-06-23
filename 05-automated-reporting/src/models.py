"""Data shapes for the automated-reporting pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MetricSnapshot:
    """A single metric's value for one source in one period.

    The atomic unit pulled from a source connector: "for period P, source S reported
    metric M = value".
    """

    source: str
    metric: str
    value: float
    period: str

    @classmethod
    def from_dict(cls, source: str, period: str, metric: str, value: Any) -> "MetricSnapshot":
        return cls(source=source, metric=metric, value=float(value), period=period)


@dataclass
class ReportRow:
    """One metric after current-vs-prior comparison, ready to render."""

    source: str
    metric: str
    display_name: str
    value: float
    previous: float
    delta: float
    pct_change: Optional[float]  # None when there is no prior value to divide by
    direction: str  # 'up' | 'down' | 'flat'
    highlighted: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "metric": self.metric,
            "display_name": self.display_name,
            "value": self.value,
            "previous": self.previous,
            "delta": self.delta,
            "pct_change": self.pct_change,
            "direction": self.direction,
            "highlighted": self.highlighted,
        }


@dataclass
class Report:
    """A rendered period report: the rows plus the period it covers."""

    period: str
    previous_period: str
    generated_for: str
    rows: List[ReportRow] = field(default_factory=list)

    @property
    def highlights(self) -> List[ReportRow]:
        return [r for r in self.rows if r.highlighted]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period": self.period,
            "previous_period": self.previous_period,
            "generated_for": self.generated_for,
            "rows": [r.to_dict() for r in self.rows],
        }
