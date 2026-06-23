"""Provisioning client.

A thin, idempotent client that executes one onboarding step for one deal. The demo backs it
with the shared JsonStore (a local file); a real one swaps each step's `_run_step` body for the
matching API call (create an auth account, spin up a workspace, add a billing subscription, send
an email, book a kickoff) wrapped in the same retry decorator.

Idempotency: each (deal, step) is keyed `deal_id:step`, so re-provisioning an already-completed
step is a no-op that returns False instead of doing the work twice — the single most common bug
in hand-rolled onboarding automations (double-charged billing, duplicate welcome emails).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from shared.retry import retry
from shared.store import JsonStore


def _key(deal_id: str, step: str) -> str:
    """Composite idempotency key: one record per (deal, step)."""
    return f"{deal_id}:{step}"


class ProvisioningClient:
    """Idempotent executor for onboarding steps, backed by JsonStore."""

    def __init__(self, store_path: str | Path):
        self._store = JsonStore(store_path)

    @retry(attempts=3, base_delay=0.2, exceptions=(ConnectionError, TimeoutError))
    def provision(self, step: str, deal_id: str, context: Dict[str, Any] | None = None) -> bool:
        """Run ``step`` for ``deal_id`` exactly once. Returns True if newly provisioned.

        If the (deal, step) is already recorded, this is a no-op and returns False — that is what
        makes a re-run safe. The @retry wrapper is what a real network call needs; here it's a
        no-op safety net that also documents the production failure mode (transient errors).
        """
        if not deal_id:
            raise ValueError("deal_id is required to provision a step")
        if not step:
            raise ValueError("step is required to provision")

        key = _key(deal_id, step)
        if self._store.get(key) is not None:
            return False  # already done — idempotent skip, no work repeated.

        record = self._run_step(step, deal_id, context or {})
        self._store.upsert(key, record)
        return True

    def _run_step(self, step: str, deal_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Swap this single method for the real per-step API calls (a dispatch on `step`).
        return {"deal_id": deal_id, "step": step, "provisioned": True, "context": context}

    def is_done(self, step: str, deal_id: str) -> bool:
        return self._store.get(_key(deal_id, step)) is not None

    def count(self) -> int:
        return len(self._store)
