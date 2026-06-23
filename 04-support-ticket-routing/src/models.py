"""Data shapes for the support-ticket pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Ticket:
    """A raw inbound support message, as it arrives from a helpdesk or inbox webhook."""

    id: str
    sender: str = ""
    subject: str = ""
    body: str = ""
    received_at: str = ""  # fixed ISO-8601 timestamp; never datetime.now() in tested logic
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """Subject + body lowercased — the surface the classifier reads."""
        return f"{self.subject}\n{self.body}".lower()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Ticket":
        return cls(
            id=str(d.get("id", "")).strip(),
            sender=str(d.get("sender", "")).strip().lower(),
            subject=str(d.get("subject", "")).strip(),
            body=str(d.get("body", "")).strip(),
            received_at=str(d.get("received_at", "")).strip(),
            raw=d,
        )


@dataclass
class Classification:
    """The classifier's verdict on a ticket."""

    topic: str
    urgency: str  # high | normal | low
    sentiment: str  # negative | neutral
    reasons: List[str] = field(default_factory=list)


@dataclass
class RoutedTicket:
    """A ticket after classification + routing, ready to track against an SLA."""

    ticket: Ticket
    classification: Classification
    queue: str
    assignee: str
    priority: str  # mirrors urgency; the field the Switch node keys on
    sla_deadline: str  # fixed ISO-8601 deadline computed from received_at
    escalate: bool

    def to_record(self) -> Dict[str, Any]:
        """Flatten into the record shape stored in the ticket store (keyed by ticket id)."""
        return {
            "id": self.ticket.id,
            "sender": self.ticket.sender,
            "subject": self.ticket.subject,
            "received_at": self.ticket.received_at,
            "topic": self.classification.topic,
            "urgency": self.classification.urgency,
            "sentiment": self.classification.sentiment,
            "reasons": self.classification.reasons,
            "queue": self.queue,
            "assignee": self.assignee,
            "priority": self.priority,
            "sla_deadline": self.sla_deadline,
            "escalate": self.escalate,
        }
