"""Data shapes for the lead pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Lead:
    """A raw inbound lead, as it arrives from a form or ad webhook."""

    email: str
    name: str = ""
    company: str = ""
    message: str = ""
    source: str = "unknown"
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def domain(self) -> str:
        """The email domain, lowercased (empty string if malformed)."""
        return self.email.split("@", 1)[1].lower() if "@" in self.email else ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Lead":
        return cls(
            email=str(d.get("email", "")).strip().lower(),
            name=str(d.get("name", "")).strip(),
            company=str(d.get("company", "")).strip(),
            message=str(d.get("message", "")).strip(),
            source=str(d.get("source", "unknown")).strip() or "unknown",
            raw=d,
        )


@dataclass
class ScoredLead:
    """A lead after enrichment + ICP scoring, ready to write to the CRM."""

    lead: Lead
    enrichment: Dict[str, Any]
    score: int
    tier: str
    reasons: list[str]
    next_action: str

    def to_record(self) -> Dict[str, Any]:
        """Flatten into the record shape stored in the CRM."""
        return {
            "email": self.lead.email,
            "name": self.lead.name,
            "company": self.lead.company or self.enrichment.get("company_guess", ""),
            "source": self.lead.source,
            "score": self.score,
            "tier": self.tier,
            "reasons": self.reasons,
            "next_action": self.next_action,
            "enrichment": self.enrichment,
        }
