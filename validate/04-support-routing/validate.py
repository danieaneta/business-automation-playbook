"""Real-data validation harness for blueprint 04 (support ticket routing).

Ingests REAL-schema labeled CFPB consumer complaints, runs the blueprint's OWN
`classify()` + `route()` (imported, never reimplemented), and reports how often
the keyword classifier's predicted topic matches the CFPB Product -> topic label
from `adapter.py`.

Run:
    python validate.py

Output is ASCII-only (Windows cp1252 safe): printed to stdout AND written to
`report.md` in this folder. No unicode arrows/emoji -- '->' only.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

# adapter.py performs the sys.path bootstrap and re-exports the blueprint Ticket.
from adapter import (
    expected_topic,
    narrative_of,
    to_ticket,
    VALID_TOPICS,
    VALIDATE_DIR,
)

# Blueprint engine -- imported, NOT reimplemented.
from src.classifier import classify
from src.routing import route

DATA_PATH = VALIDATE_DIR / "data" / "cfpb_sample.json"
REPORT_PATH = VALIDATE_DIR / "report.md"


def load_records(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array of CFPB records")
    return data


def run() -> str:
    records = load_records(DATA_PATH)

    total = len(records)
    skipped = 0          # empty / whitespace-only narrative
    scored = 0           # rows actually classified + scored
    matches = 0          # predicted topic == expected topic

    # per-expected-topic tallies: expected -> {"n": int, "hit": int}
    per_topic: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "hit": 0})
    # confusion of where the classifier sent each expected topic
    examples: list[tuple[str, str, str, bool]] = []  # (subject, predicted, expected, ok)

    for rec in records:
        if not narrative_of(rec):
            skipped += 1
            continue

        ticket = to_ticket(rec)
        classification = classify(ticket)          # blueprint engine
        routed = route(ticket, classification)     # blueprint engine
        predicted = classification.topic
        exp = expected_topic(rec)

        ok = predicted == exp
        scored += 1
        matches += int(ok)
        per_topic[exp]["n"] += 1
        per_topic[exp]["hit"] += int(ok)
        examples.append(
            (ticket.subject or "(no subject)", predicted, exp, ok)
        )
        # touch routed so the routing path is genuinely exercised, not just classify
        _ = routed.queue

    accuracy = (matches / scored * 100.0) if scored else 0.0

    # ---- build ASCII report ----
    lines: list[str] = []
    lines.append("# Blueprint 04 -- CFPB Real-Data Routing Validation")
    lines.append("")
    lines.append("Engine: imported from 04-support-ticket-routing/src (classify + route).")
    lines.append("Data:   data/cfpb_sample.json (CFPB-schema consumer complaints).")
    lines.append("Label:  CFPB Product -> support topic (see adapter.py; a coarse proxy).")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"Total records:           {total}")
    lines.append(f"Skipped (empty narrative): {skipped}")
    lines.append(f"Scored:                  {scored}")
    lines.append(f"Routing-match accuracy:  {accuracy:.1f}%  ({matches}/{scored})")
    lines.append("")
    lines.append("## Per-topic breakdown (expected topic -> match rate)")
    lines.append("")
    lines.append("    topic       scored   matched   rate")
    lines.append("    ---------   ------   -------   -----")
    for topic in sorted(per_topic.keys()):
        n = per_topic[topic]["n"]
        hit = per_topic[topic]["hit"]
        rate = (hit / n * 100.0) if n else 0.0
        lines.append(f"    {topic:<9}   {n:>6}   {hit:>7}   {rate:>4.0f}%")
    lines.append("")
    lines.append("## 5 worked examples (subject -> predicted vs expected)")
    lines.append("")
    for subject, predicted, exp, ok in examples[:5]:
        flag = "OK " if ok else "MISS"
        subj = subject if len(subject) <= 52 else subject[:49] + "..."
        lines.append(f"    [{flag}] {subj}")
        lines.append(f"           predicted: {predicted:<10} expected: {exp}")
    lines.append("")
    lines.append("Note: topics in scope are billing/technical/account/sales/general.")
    lines.append("CFPB is a financial-product taxonomy and does not map cleanly to a")
    lines.append("support desk, so this measures routing behaviour, not gold-label accuracy.")
    lines.append("")

    report = "\n".join(lines)

    # Ensure ASCII-only (cp1252 safe). Replace any stray non-ascii defensively.
    report = report.encode("ascii", "replace").decode("ascii")
    return report


def main() -> int:
    report = run()
    # print to stdout
    print(report)
    # write report.md (ascii / newline-normalised)
    with open(REPORT_PATH, "w", encoding="ascii", newline="\n") as f:
        f.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
