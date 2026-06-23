"""Data shapes for the client-onboarding pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

VALID_PLANS = ("smb", "pro", "enterprise")


@dataclass
class WonDeal:
    """A deal marked "Won" in the CRM — the trigger for post-sale onboarding."""

    deal_id: str
    company: str = ""
    contact_email: str = ""
    plan: str = "smb"
    seats: int = 1
    signed_at: str = ""  # ISO-8601 date/time the deal closed; kept as a string for determinism.
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WonDeal":
        plan = str(d.get("plan", "smb")).strip().lower() or "smb"
        try:
            seats = int(d.get("seats", 1))
        except (TypeError, ValueError):
            seats = 1
        return cls(
            deal_id=str(d.get("deal_id", "")).strip(),
            company=str(d.get("company", "")).strip(),
            contact_email=str(d.get("contact_email", "")).strip().lower(),
            plan=plan,
            seats=max(seats, 0),
            signed_at=str(d.get("signed_at", "")).strip(),
            raw=d,
        )

    @property
    def is_valid(self) -> bool:
        """A deal we can act on: has an id and a known plan."""
        return bool(self.deal_id) and self.plan in VALID_PLANS


@dataclass
class OnboardingResult:
    """The outcome of onboarding one won deal across its required checklist steps."""

    deal: WonDeal
    required_steps: List[str]
    completed: List[str] = field(default_factory=list)   # provisioned this run
    skipped: List[str] = field(default_factory=list)      # already done on a prior run
    failed: List[str] = field(default_factory=list)       # raised after retries
    sla_hours: int = 0

    @property
    def done_count(self) -> int:
        """Steps that are in a finished state (newly completed OR already done)."""
        return len(self.completed) + len(self.skipped)

    @property
    def percent_complete(self) -> int:
        """Whole-number percent of required steps that are finished."""
        if not self.required_steps:
            return 100
        return round(100 * self.done_count / len(self.required_steps))

    @property
    def status(self) -> str:
        if self.failed:
            return "incomplete"
        if self.completed and not self.skipped:
            return "onboarded"
        if self.skipped and not self.completed:
            return "already_onboarded"
        return "onboarded"

    def to_record(self) -> Dict[str, Any]:
        """Flatten into the record shape stored as the onboarding summary."""
        return {
            "deal_id": self.deal.deal_id,
            "company": self.deal.company,
            "contact_email": self.deal.contact_email,
            "plan": self.deal.plan,
            "seats": self.deal.seats,
            "signed_at": self.deal.signed_at,
            "required_steps": self.required_steps,
            "completed": self.completed,
            "skipped": self.skipped,
            "failed": self.failed,
            "percent_complete": self.percent_complete,
            "status": self.status,
            "sla_hours": self.sla_hours,
        }
