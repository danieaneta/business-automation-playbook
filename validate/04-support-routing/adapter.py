"""Adapter: CFPB Consumer Complaint record -> blueprint 04 `Ticket` + an expected topic.

This module is the only place that knows the CFPB schema. It does two jobs:

1. `to_ticket(record)` maps a raw CFPB complaint dict to the blueprint's `Ticket`
   dataclass (imported from the real blueprint -- we never redefine it here).
2. `expected_topic(record)` maps the CFPB `Product` to ONE of the support-desk
   topics the blueprint routes on: billing / technical / account / sales / general.

HONESTY NOTE ON THE MAPPING
---------------------------
CFPB is a *financial-product* taxonomy (mortgages, debt collection, credit
reporting...). The blueprint is a generic *support-desk* taxonomy
(billing/technical/account/sales/general). These do NOT line up cleanly, so the
Product->topic table below is a best-effort, deliberately-coarse proxy, not
ground truth. A "mortgage" complaint could be billing, account, or general
depending on the narrative; we pick the single most representative bucket per
Product so we have a stable label to score against.

What this harness therefore measures is **routing behaviour and stability** --
"does the keyword classifier send a real, messy consumer narrative to a sensible
queue?" -- NOT classification accuracy against a gold support-desk label set
(which does not exist for this data). Read the accuracy number in that light.

The path bootstrap below is copied from the blueprint's `run.py` / `conftest.py`
so that `from src... import ...` and `from shared... import ...` resolve whether
this is run from here, the blueprint dir, or the repo root.
"""

from __future__ import annotations

import sys
from pathlib import Path

# --- path bootstrap (mirrors 04-support-ticket-routing/run.py + conftest.py) ---
VALIDATE_DIR = Path(__file__).resolve().parent              # validate/04-support-routing
REPO_ROOT = VALIDATE_DIR.parent.parent                      # repo root
BLUEPRINT_DIR = REPO_ROOT / "04-support-ticket-routing"     # the blueprint we reuse
for _p in (str(BLUEPRINT_DIR), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
# -------------------------------------------------------------------------------

from src.models import Ticket  # noqa: E402  (imported AFTER bootstrap, on purpose)


# CFPB Product (exact strings from the public schema) -> expected support topic.
# Topics MUST be one of: billing | technical | account | sales | general.
#
# Rationale per row:
#   - Credit card / prepaid card  -> billing  (statements, charges, fees, refunds)
#   - Mortgage                    -> billing  (payments, escrow, payoff invoices)
#   - Vehicle loan or lease       -> billing  (loan payments / payoff amounts)
#   - Student loan                -> billing  (servicing, payment handling)
#   - Payday/title/personal loan  -> billing  (fees, interest, payoff)
#   - Checking or savings account -> account  (access, opening/closing, managing)
#   - Money transfer / wallet / crypto -> technical (apps, platforms, transactions)
#   - Debt collection             -> general  (disputes/communication; no clean desk bucket)
#   - Credit reporting / repair   -> general  (report disputes; no clean desk bucket)
#
# NOTE: there is no CFPB Product that corresponds to a "sales" support topic, so
# `sales` is intentionally absent from this table. A handful of narratives in the
# sample mention demos/quotes/upgrades and may still classify as sales from
# keywords -- that surfaces as a mismatch, which is honest signal about the
# keyword classifier, not a labelling bug.
PRODUCT_TO_TOPIC = {
    "Credit card or prepaid card": "billing",
    "Mortgage": "billing",
    "Vehicle loan or lease": "billing",
    "Student loan": "billing",
    "Payday loan, title loan, or personal loan": "billing",
    "Checking or savings account": "account",
    "Money transfer, virtual currency, or money service": "technical",
    "Debt collection": "general",
    "Credit reporting, credit repair services, or other personal consumer reports": "general",
}

VALID_TOPICS = {"billing", "technical", "account", "sales", "general"}


def _to_iso(date_received: str) -> str:
    """CFPB 'Date received' is 'YYYY-MM-DD'. Normalise to an ISO-8601 datetime
    (midnight UTC) so the blueprint's SLA math has a parseable timestamp."""
    d = (date_received or "").strip()
    if not d:
        return ""
    # Already a full timestamp? leave it. Otherwise add a midnight-UTC time.
    if "T" in d:
        return d
    return f"{d}T00:00:00+00:00"


def narrative_of(record: dict) -> str:
    """The consumer narrative, stripped. May be '' / whitespace -> caller skips."""
    return str(record.get("Consumer complaint narrative", "") or "").strip()


def to_ticket(record: dict) -> Ticket:
    """Map one CFPB complaint record to a blueprint `Ticket`.

    id      <- Complaint ID
    subject <- Issue            (the short consumer-selected problem label)
    body    <- Consumer complaint narrative
    received_at <- Date received (as ISO-8601)
    raw     <- the original record (kept for traceability)
    """
    return Ticket(
        id=str(record.get("Complaint ID", "")).strip(),
        sender="",  # CFPB does not expose a consumer email (PII); leave blank.
        subject=str(record.get("Issue", "")).strip(),
        body=narrative_of(record),
        received_at=_to_iso(str(record.get("Date received", ""))),
        raw=record,
    )


def expected_topic(record: dict) -> str:
    """Mapped expected support topic for a CFPB record. Unknown Product -> 'general'."""
    product = str(record.get("Product", "")).strip()
    return PRODUCT_TO_TOPIC.get(product, "general")
