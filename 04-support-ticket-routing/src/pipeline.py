"""Support-ticket pipeline orchestrator.

The end-to-end flow that the n8n workflow mirrors visually:

    inbound ticket  ->  classify  ->  route  ->  upsert to store (idempotent)  ->  flag SLA breaches

Timing is deterministic: breaches are evaluated against a fixed `as_of` timestamp, never
datetime.now(). Every step emits a structured log line, so a run is fully auditable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from shared.logging_config import get_logger

from .classifier import classify
from .config import DEFAULT_ROUTING, RoutingConfig
from .models import RoutedTicket, Ticket
from .routing import is_breaching, route
from .ticket_store import TicketStore

logger = get_logger("ticket_pipeline")

# Paths relative to the blueprint folder (this file lives in <blueprint>/src/).
BLUEPRINT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = BLUEPRINT_DIR / "data" / "sample_tickets.json"
DEFAULT_STORE = BLUEPRINT_DIR / "data" / "tickets_store.json"

# Fixed "now" for the demo so SLA breach output is deterministic across runs/machines.
DEFAULT_AS_OF = "2026-06-23T12:00:00+00:00"


def process_ticket(ticket: Ticket, store: TicketStore, cfg: RoutingConfig = DEFAULT_ROUTING) -> RoutedTicket:
    """Run one ticket through classify -> route -> upsert and return the routed result."""
    classification = classify(ticket, cfg)
    routed = route(ticket, classification, cfg)
    created = store.upsert_ticket(routed.to_record())
    logger.info(
        "ticket processed",
        extra={"context": {
            "id": ticket.id, "topic": classification.topic, "priority": routed.priority,
            "queue": routed.queue, "escalate": routed.escalate, "store_created": created,
        }},
    )
    return routed


def run_pipeline(
    raw_tickets: Iterable[Dict[str, Any]],
    store_path: str | Path = DEFAULT_STORE,
    cfg: RoutingConfig = DEFAULT_ROUTING,
) -> List[RoutedTicket]:
    """Process a batch of raw ticket dicts. Returns the routed tickets."""
    store = TicketStore(store_path)
    results: List[RoutedTicket] = []
    for raw in raw_tickets:
        ticket = Ticket.from_dict(raw)
        if not ticket.id or not ticket.received_at:
            logger.warning("skipping ticket missing id or received_at", extra={"context": {"raw": raw}})
            continue
        results.append(process_ticket(ticket, store, cfg))
    logger.info(
        "batch complete",
        extra={"context": {"processed": len(results), "store_total": store.count()}},
    )
    return results


def main(
    input_path: str | Path = DEFAULT_INPUT,
    store_path: str | Path = DEFAULT_STORE,
    as_of: str = DEFAULT_AS_OF,
) -> None:
    raw_tickets = json.loads(Path(input_path).read_text(encoding="utf-8"))
    results = run_pipeline(raw_tickets, store_path)

    # Collapse duplicate ticket ids (the store is keyed by id) so counts match the store, not the
    # raw row count. Last write wins, mirroring the idempotent upsert.
    unique: Dict[str, RoutedTicket] = {r.ticket.id: r for r in results}

    by_priority: Dict[str, int] = {}
    by_queue: Dict[str, int] = {}
    breaching: List[RoutedTicket] = []
    for r in unique.values():
        by_priority[r.priority] = by_priority.get(r.priority, 0) + 1
        by_queue[r.queue] = by_queue.get(r.queue, 0) + 1
        if is_breaching(r, as_of):
            breaching.append(r)

    print("\n=== Support ticket routing run summary ===")
    print(f"Processed: {len(results)} rows -> {len(unique)} unique tickets  (as of {as_of})")

    print("\nBy priority:")
    for priority in ("high", "normal", "low"):
        if priority in by_priority:
            print(f"  {priority:>6}: {by_priority[priority]}")

    print("\nBy queue:")
    for queue in sorted(by_queue):
        print(f"  {queue:<20} {by_queue[queue]}")

    print(f"\nSLA breaching: {len(breaching)}")
    for r in breaching:
        print(f"  [{r.priority:>6}] {r.ticket.id:<8} {r.queue:<18} due {r.sla_deadline}")

    print(f"\nTicket store written to: {store_path}")


if __name__ == "__main__":
    main()
