"""Data shapes for the invoicing pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List


def _parse_date(value: Any) -> date:
    """Coerce an ISO date string (or date) into a ``date``. Empty -> raises."""
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


@dataclass
class UsageRecord:
    """One billable line of usage for a client within a period."""

    client_id: str
    description: str
    qty: float
    unit_price: float
    date: date

    @property
    def amount(self) -> float:
        """Line amount before tax (qty * unit_price), rounded to 2dp."""
        return round(self.qty * self.unit_price, 2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "UsageRecord":
        return cls(
            client_id=str(d.get("client_id", "")).strip(),
            description=str(d.get("description", "")).strip(),
            qty=float(d.get("qty", 0)),
            unit_price=float(d.get("unit_price", 0)),
            date=_parse_date(d.get("date")),
        )


@dataclass
class Invoice:
    """A built invoice: line items plus computed money fields and a due date."""

    id: str
    client_id: str
    period: str
    line_items: List[Dict[str, Any]]
    subtotal: float
    tax: float
    total: float
    due_date: date
    currency: str = "USD"
    status: str = "open"
    amount_paid: float = 0.0

    @property
    def balance_due(self) -> float:
        """What's still owed, rounded to 2dp."""
        return round(self.total - self.amount_paid, 2)

    def days_overdue(self, as_of: date) -> int:
        """Whole days past the due date as of ``as_of`` (0 if not yet due)."""
        return max((as_of - self.due_date).days, 0)

    def to_record(self) -> Dict[str, Any]:
        """Flatten into the record shape stored in the ledger."""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "period": self.period,
            "line_items": self.line_items,
            "subtotal": self.subtotal,
            "tax": self.tax,
            "total": self.total,
            "due_date": self.due_date.isoformat(),
            "currency": self.currency,
            "status": self.status,
            "amount_paid": self.amount_paid,
        }


@dataclass
class Payment:
    """A payment a client made against an invoice."""

    client_id: str
    invoice_id: str
    amount: float
    paid_at: date
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Payment":
        return cls(
            client_id=str(d.get("client_id", "")).strip(),
            invoice_id=str(d.get("invoice_id", "")).strip(),
            amount=float(d.get("amount", 0)),
            paid_at=_parse_date(d.get("paid_at")),
            raw=d,
        )
