"""Lead → CRM pipeline orchestrator.

The end-to-end flow that the n8n workflow mirrors visually:

    raw lead  →  enrich  →  score against ICP  →  upsert to CRM (idempotent)  →  decide follow-up

Every step emits a structured log line, so a run is fully auditable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from shared.logging_config import get_logger

from .config import DEFAULT_ICP, ICPConfig
from .crm_client import CRMClient
from .enrichment import enrich_lead
from .models import Lead, ScoredLead
from .scoring import score_lead

logger = get_logger("lead_pipeline")

# Paths relative to the blueprint folder (this file lives in <blueprint>/src/).
BLUEPRINT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = BLUEPRINT_DIR / "data" / "sample_leads.json"
DEFAULT_STORE = BLUEPRINT_DIR / "data" / "crm_store.json"


def process_lead(lead: Lead, crm: CRMClient, icp: ICPConfig = DEFAULT_ICP) -> ScoredLead:
    """Run one lead through enrich → score → upsert and return the scored result."""
    enrichment = enrich_lead(lead, icp)
    score, tier, reasons, action = score_lead(lead, enrichment, icp)
    scored = ScoredLead(
        lead=lead, enrichment=enrichment, score=score, tier=tier, reasons=reasons, next_action=action
    )
    created = crm.upsert_lead(scored.to_record())
    logger.info(
        "lead processed",
        extra={"context": {
            "email": lead.email, "score": score, "tier": tier,
            "next_action": action, "crm_created": created,
        }},
    )
    return scored


def run_pipeline(
    raw_leads: Iterable[Dict[str, Any]],
    store_path: str | Path = DEFAULT_STORE,
    icp: ICPConfig = DEFAULT_ICP,
) -> List[ScoredLead]:
    """Process a batch of raw lead dicts. Returns the scored leads."""
    crm = CRMClient(store_path)
    results: List[ScoredLead] = []
    for raw in raw_leads:
        lead = Lead.from_dict(raw)
        if "@" not in lead.email or "." not in lead.domain:
            logger.warning("skipping lead with invalid email", extra={"context": {"raw": raw}})
            continue
        results.append(process_lead(lead, crm, icp))
    logger.info(
        "batch complete",
        extra={"context": {"processed": len(results), "crm_total": crm.count()}},
    )
    return results


def main(input_path: str | Path = DEFAULT_INPUT, store_path: str | Path = DEFAULT_STORE) -> None:
    raw_leads = json.loads(Path(input_path).read_text(encoding="utf-8"))
    results = run_pipeline(raw_leads, store_path)

    by_tier: Dict[str, int] = {}
    for r in results:
        by_tier[r.tier] = by_tier.get(r.tier, 0) + 1

    print("\n=== Lead -> CRM run summary ===")
    print(f"Processed: {len(results)} leads")
    for tier in ("hot", "warm", "cold"):
        if tier in by_tier:
            print(f"  {tier:>4}: {by_tier[tier]}")
    print("\nTop leads:")
    for r in sorted(results, key=lambda s: s.score, reverse=True)[:5]:
        print(f"  [{r.score:>3}] {r.tier:>4}  {r.lead.email:<32} -> {r.next_action}")
    print(f"\nCRM store written to: {store_path}")


if __name__ == "__main__":
    main()
