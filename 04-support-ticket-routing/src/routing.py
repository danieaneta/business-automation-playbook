"""Routing + SLA logic.

`route` turns a ticket + classification into a queue, an assignee, a priority, an SLA deadline,
and an escalation flag. `sla_deadline` and `is_breaching` are deterministic: all timing comes
from explicit ISO timestamps (received_at / as_of), never datetime.now(), so the SLA behaviour
is fully testable.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .config import DEFAULT_ROUTING, RoutingConfig
from .models import Classification, RoutedTicket, Ticket


def _parse_iso(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp. Accepts a trailing 'Z' (UTC)."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def sla_deadline(classification: Classification, received_at: str, cfg: RoutingConfig = DEFAULT_ROUTING) -> str:
    """Return the ISO-8601 deadline = received_at + SLA window for the ticket's urgency."""
    start = _parse_iso(received_at)
    minutes = cfg.sla_for(classification.urgency)
    return (start + timedelta(minutes=minutes)).isoformat()


def is_breaching(routed: RoutedTicket, as_of: str) -> bool:
    """True if the ticket's SLA deadline is at or before `as_of` (a fixed ISO timestamp)."""
    return _parse_iso(as_of) >= _parse_iso(routed.sla_deadline)


def route(ticket: Ticket, classification: Classification, cfg: RoutingConfig = DEFAULT_ROUTING) -> RoutedTicket:
    """Route a classified ticket to a queue + assignee, with priority and SLA deadline."""
    escalate = classification.urgency == cfg.escalate_urgency
    queue = cfg.oncall_queue if escalate else cfg.queue_for(classification.topic)
    assignee = "on-call-engineer" if escalate else f"{classification.topic}-team"
    deadline = sla_deadline(classification, ticket.received_at, cfg)

    return RoutedTicket(
        ticket=ticket,
        classification=classification,
        queue=queue,
        assignee=assignee,
        priority=classification.urgency,
        sla_deadline=deadline,
        escalate=escalate,
    )
