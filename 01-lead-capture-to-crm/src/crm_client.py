"""CRM client.

A thin, idempotent client that writes scored leads to a "CRM". The demo backs it with the
shared JsonStore (a local file); a real one swaps the `_write` body for a HubSpot/Pipedrive/
GoHighLevel API call wrapped in the same retry decorator.

Idempotency: leads are keyed by email, so re-processing the same lead updates one record
instead of creating a duplicate — the single most common bug in hand-rolled lead automations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from shared.retry import retry
from shared.store import JsonStore


class CRMClient:
    """Idempotent upsert interface to the CRM."""

    def __init__(self, store_path: str | Path):
        self._store = JsonStore(store_path)

    @retry(attempts=3, base_delay=0.2, exceptions=(ConnectionError, TimeoutError))
    def upsert_lead(self, record: Dict[str, Any]) -> bool:
        """Upsert a lead record keyed by email. Returns True if newly created.

        The @retry wrapper is what a real network call needs; here it's a no-op safety net that
        also documents the production failure mode (transient connection/timeout errors).
        """
        email = record.get("email")
        if not email:
            raise ValueError("record is missing required 'email' key")
        return self._write(email, record)

    def _write(self, key: str, record: Dict[str, Any]) -> bool:
        # Swap this single method for the real API call (POST/PATCH by external id).
        return self._store.upsert(key, record)

    def get_lead(self, email: str) -> Dict[str, Any] | None:
        return self._store.get(email)

    def count(self) -> int:
        return len(self._store)
