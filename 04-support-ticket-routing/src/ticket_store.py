"""Ticket store.

A thin, idempotent client that writes routed tickets to a "helpdesk". The demo backs it with
the shared JsonStore (a local file); a real one swaps the `_write` body for a Zendesk/Freshdesk/
Intercom API call wrapped in the same retry decorator.

Idempotency: tickets are keyed by ticket id, so re-processing the same ticket updates one record
instead of creating a duplicate — the single most common bug in hand-rolled ticket automations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from shared.retry import retry
from shared.store import JsonStore


class TicketStore:
    """Idempotent upsert interface to the helpdesk, keyed by ticket id."""

    def __init__(self, store_path: str | Path):
        self._store = JsonStore(store_path)

    @retry(attempts=3, base_delay=0.2, exceptions=(ConnectionError, TimeoutError))
    def upsert_ticket(self, record: Dict[str, Any]) -> bool:
        """Upsert a ticket record keyed by id. Returns True if newly created.

        The @retry wrapper is what a real network call needs; here it's a no-op safety net that
        also documents the production failure mode (transient connection/timeout errors).
        """
        ticket_id = record.get("id")
        if not ticket_id:
            raise ValueError("record is missing required 'id' key")
        return self._write(ticket_id, record)

    def _write(self, key: str, record: Dict[str, Any]) -> bool:
        # Swap this single method for the real API call (POST/PATCH by ticket id).
        return self._store.upsert(key, record)

    def get_ticket(self, ticket_id: str) -> Dict[str, Any] | None:
        return self._store.get(ticket_id)

    def count(self) -> int:
        return len(self._store)
