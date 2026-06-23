"""Automated-reporting pipeline orchestrator.

The end-to-end flow that the n8n workflow mirrors visually:

    schedule  ->  fetch KPIs from each source  ->  compare vs prior period  ->  render digest
              ->  deliver (idempotent, keyed by period)  ->  summary

Every step emits a structured log line, so a run is fully auditable. The period and prior period
come from the sample data / parameters (never datetime.now()), so the pipeline is deterministic
and testable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from shared.logging_config import get_logger

from .config import DEFAULT_REPORT, ReportConfig
from .connectors import DEFAULT_METRICS_FILE, MetricSource
from .delivery import DeliveryResult, Deliverer
from .digest import render_digest
from .models import MetricSnapshot, Report
from .transform import compare

logger = get_logger("report_pipeline")

# Paths relative to the blueprint folder (this file lives in <blueprint>/src/).
BLUEPRINT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_METRICS = DEFAULT_METRICS_FILE
DEFAULT_STORE = BLUEPRINT_DIR / "data" / "delivery_store.json"

# Fixed period labels used by the demo so runs are deterministic.
DEFAULT_PERIOD = "2026-W24"
DEFAULT_PREVIOUS_PERIOD = "2026-W23"
DEFAULT_GENERATED_FOR = "Acme Inc"


def build_report(
    period: str = DEFAULT_PERIOD,
    previous_period: str = DEFAULT_PREVIOUS_PERIOD,
    generated_for: str = DEFAULT_GENERATED_FOR,
    metrics_file: str | Path = DEFAULT_METRICS,
    config: ReportConfig = DEFAULT_REPORT,
) -> Report:
    """Fetch every source for both periods, compare, and assemble the Report."""
    source = MetricSource(metrics_file)

    current: List[MetricSnapshot] = []
    previous: List[MetricSnapshot] = []
    for src in config.sources:
        cur = source.fetch_metrics(src, period)
        prev = source.fetch_metrics(src, previous_period)
        current.extend(cur)
        previous.extend(prev)
        logger.info(
            "source fetched",
            extra={"context": {"source": src, "period": period, "metrics": len(cur)}},
        )

    rows = compare(current, previous, config)
    return Report(
        period=period,
        previous_period=previous_period,
        generated_for=generated_for,
        rows=rows,
    )


def run_pipeline(
    period: str = DEFAULT_PERIOD,
    previous_period: str = DEFAULT_PREVIOUS_PERIOD,
    generated_for: str = DEFAULT_GENERATED_FOR,
    metrics_file: str | Path = DEFAULT_METRICS,
    store_path: str | Path = DEFAULT_STORE,
    config: ReportConfig = DEFAULT_REPORT,
) -> Dict[str, Any]:
    """Build the report, render it, deliver idempotently, and return a summary dict."""
    report = build_report(period, previous_period, generated_for, metrics_file, config)
    digest = render_digest(report)

    deliverer = Deliverer(store_path, channel=config.channel)
    result: DeliveryResult = deliverer.deliver(digest, period)

    logger.info(
        "report run complete",
        extra={"context": {
            "period": period,
            "metrics": len(report.rows),
            "highlights": len(report.highlights),
            "delivery": result.status,
        }},
    )
    return {
        "report": report,
        "digest": digest,
        "delivery": result,
        "metrics_reported": len(report.rows),
        "highlights": len(report.highlights),
    }


def main(
    period: str = DEFAULT_PERIOD,
    previous_period: str = DEFAULT_PREVIOUS_PERIOD,
    metrics_file: str | Path = DEFAULT_METRICS,
    store_path: str | Path = DEFAULT_STORE,
) -> None:
    summary = run_pipeline(
        period=period,
        previous_period=previous_period,
        metrics_file=metrics_file,
        store_path=store_path,
    )
    report: Report = summary["report"]
    result: DeliveryResult = summary["delivery"]

    print("\n=== Rendered digest ===\n")
    print(summary["digest"])

    print("\n=== Automated reporting run summary ===")
    print(f"Period:    {report.period} (vs {report.previous_period})")
    print(f"Metrics:   {summary['metrics_reported']} reported")
    print(f"Highlights:{summary['highlights']:>3} big movers")
    print(f"Delivery:  {result.status} -> {result.channel}")
    if not result.delivered:
        print("           (already delivered for this period; re-run was idempotent)")
    print("\nBig movers:")
    if report.highlights:
        for r in report.highlights:
            arrow = "up" if r.direction == "up" else ("down" if r.direction == "down" else "flat")
            pct = "new" if r.pct_change is None else f"{r.pct_change:+.1f}%"
            print(f"  {arrow:>4}  {r.display_name:<22} {pct}")
    else:
        print("  (none cleared the highlight threshold)")
    print(f"\nDelivery log written to: {store_path}")


if __name__ == "__main__":
    main()
