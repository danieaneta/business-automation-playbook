"""Digest delivery.

Delivers the rendered digest to a channel (Slack/email in production). The demo backs it with
the shared JsonStore so delivery is **idempotent, keyed by period**: re-running the same
period's report does NOT re-deliver. That keying is the single most common bug in hand-rolled
report automations (a cron retry spams the channel with duplicate digests).

A real one swaps the `_send` body for a Slack/email API call wrapped in the same retry
decorator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from shared.logging_config import get_logger
from shared.retry import retry
from shared.store import JsonStore

logger = get_logger("report_delivery")


class DeliveryResult:
    """Outcome of a delivery attempt: 'delivered' (first time) or 'skipped' (already sent)."""

    def __init__(self, period: str, status: str, channel: str):
        self.period = period
        self.status = status  # 'delivered' | 'skipped'
        self.channel = channel

    @property
    def delivered(self) -> bool:
        return self.status == "delivered"

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"DeliveryResult(period={self.period!r}, status={self.status!r})"


class Deliverer:
    """Idempotent delivery interface keyed by report period."""

    def __init__(self, store_path: str | Path, channel: str = "#weekly-metrics"):
        self._store = JsonStore(store_path)
        self.channel = channel

    def deliver(self, digest: str, period: str) -> DeliveryResult:
        """Deliver the digest for ``period`` exactly once.

        If a digest for this period was already delivered, returns a 'skipped' result and does
        NOT re-send. Otherwise sends and records the delivery.
        """
        if self._store.get(period) is not None:
            logger.info(
                "delivery skipped (already sent)",
                extra={"context": {"period": period, "channel": self.channel}},
            )
            return DeliveryResult(period, "skipped", self.channel)

        self._send(period, digest)
        self._store.upsert(period, {"period": period, "channel": self.channel, "chars": len(digest)})
        logger.info(
            "digest delivered",
            extra={"context": {"period": period, "channel": self.channel, "chars": len(digest)}},
        )
        return DeliveryResult(period, "delivered", self.channel)

    @retry(attempts=3, base_delay=0.2, exceptions=(ConnectionError, TimeoutError))
    def _send(self, period: str, digest: str) -> Dict[str, Any]:
        # Swap this single method for the real API call (Slack chat.postMessage / send email).
        # The @retry wrapper documents the production failure mode (transient network errors).
        return {"period": period, "channel": self.channel, "ok": True}

    def was_delivered(self, period: str) -> bool:
        return self._store.get(period) is not None
