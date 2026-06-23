"""Routing config: topic keywords, urgency signals, queue map, and SLA windows.

In a real deployment these live in environment variables / a config file so a support lead can
tune routing without touching code. See `.env.example` for the production-integration knobs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class RoutingConfig:
    """Defines how a ticket is classified, routed, and tracked against an SLA."""

    # Topic detection: each topic maps to the keywords that signal it. Best match wins;
    # fallback is 'general'. Order here is the tie-break order.
    topic_keywords: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "billing": ["invoice", "charge", "refund", "payment", "billing", "subscription", "pricing"],
            "technical": ["error", "bug", "crash", "outage", "down", "broken", "fails", "500", "login"],
            "account": ["password", "account", "access", "permission", "login", "reset", "locked"],
            "sales": ["demo", "quote", "upgrade", "plan", "buy", "purchase", "trial", "sales"],
        }
    )

    # Urgency signals: words that push a ticket to high or low. Default is normal.
    high_urgency_signals: List[str] = field(
        default_factory=lambda: ["urgent", "asap", "outage", "down", "critical", "emergency", "immediately"]
    )
    low_urgency_signals: List[str] = field(
        default_factory=lambda: ["whenever", "no rush", "no hurry", "low priority", "not urgent", "someday"]
    )

    # Sentiment: complaint words flag negative sentiment.
    negative_signals: List[str] = field(
        default_factory=lambda: ["angry", "frustrated", "unacceptable", "terrible", "worst", "disappointed", "ridiculous", "furious"]
    )

    # topic -> queue (where the ticket lands).
    topic_queue: Dict[str, str] = field(
        default_factory=lambda: {
            "billing": "billing-queue",
            "technical": "tech-support-queue",
            "account": "account-queue",
            "sales": "sales-queue",
            "general": "triage-queue",
        }
    )

    # SLA response windows in minutes, by urgency.
    sla_minutes: Dict[str, int] = field(
        default_factory=lambda: {"high": 60, "normal": 480, "low": 1440}
    )

    # High-urgency tickets page the on-call engineer instead of just sitting in a queue.
    escalate_urgency: str = "high"
    oncall_queue: str = "oncall-pager"

    def queue_for(self, topic: str) -> str:
        return self.topic_queue.get(topic, self.topic_queue["general"])

    def sla_for(self, urgency: str) -> int:
        return self.sla_minutes.get(urgency, self.sla_minutes["normal"])


DEFAULT_ROUTING = RoutingConfig()
