"""Digest renderer.

Turns a Report into a plain-text / markdown string a human reads in Slack or email. ASCII only
(the Windows console is cp1252): direction is shown as 'up'/'down'/'flat', a '*' marks big
movers, and there are no Unicode arrows or emoji.
"""

from __future__ import annotations

from .models import Report, ReportRow

_ARROW = {"up": "up", "down": "down", "flat": "flat"}


def _fmt_value(v: float) -> str:
    """Render a number without a trailing '.0' for whole values."""
    if float(v).is_integer():
        return f"{int(v):,}"
    return f"{v:,.2f}"


def _fmt_pct(row: ReportRow) -> str:
    if row.pct_change is None:
        return "new"
    sign = "+" if row.pct_change > 0 else ""
    return f"{sign}{row.pct_change:.1f}%"


def _fmt_delta(row: ReportRow) -> str:
    sign = "+" if row.delta > 0 else ""
    return f"{sign}{_fmt_value(row.delta)}"


def render_row(row: ReportRow) -> str:
    """One line per metric: name, value, delta, pct, direction, highlight marker."""
    marker = "* " if row.highlighted else "  "
    return (
        f"{marker}{row.display_name}: {_fmt_value(row.value)} "
        f"({_fmt_delta(row)}, {_fmt_pct(row)} {_ARROW[row.direction]} vs prior)"
    )


def render_digest(report: Report) -> str:
    """Render the whole report as an ASCII markdown digest string."""
    lines = [
        f"# Weekly Metrics Digest - {report.period}",
        f"_For {report.generated_for} (vs {report.previous_period})_",
        "",
    ]

    highlights = report.highlights
    if highlights:
        lines.append("## Highlights (big movers)")
        for row in highlights:
            lines.append(render_row(row))
        lines.append("")

    lines.append("## All metrics")
    for row in report.rows:
        lines.append(render_row(row))

    lines.append("")
    lines.append(
        f"{len(report.rows)} metrics reported, {len(highlights)} flagged as big movers "
        f"(threshold reached). '*' = big mover."
    )
    return "\n".join(lines)
