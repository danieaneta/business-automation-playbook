"""Client-onboarding pipeline orchestrator.

The end-to-end flow that the n8n workflow mirrors visually:

    deal marked Won  ->  compute required checklist (per plan)  ->  provision each step
    (idempotent)  ->  record an onboarding summary

Every deal emits a structured log line, so a run is fully auditable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from shared.logging_config import get_logger

from .config import DEFAULT_CONFIG, OnboardingConfig
from .engine import onboard_deal
from .models import OnboardingResult, WonDeal
from .provisioning_client import ProvisioningClient

logger = get_logger("onboarding_pipeline")

# Paths relative to the blueprint folder (this file lives in <blueprint>/src/).
BLUEPRINT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = BLUEPRINT_DIR / "data" / "sample_deals.json"
DEFAULT_STORE = BLUEPRINT_DIR / "data" / "onboarding_store.json"


def process_deal(
    deal: WonDeal,
    provisioner: ProvisioningClient,
    config: OnboardingConfig = DEFAULT_CONFIG,
) -> OnboardingResult:
    """Run one won deal through the onboarding checklist and return the result."""
    result = onboard_deal(deal, provisioner, config)
    logger.info(
        "deal onboarded",
        extra={"context": {
            "deal_id": deal.deal_id,
            "company": deal.company,
            "plan": deal.plan,
            "completed": len(result.completed),
            "skipped": len(result.skipped),
            "failed": len(result.failed),
            "percent_complete": result.percent_complete,
            "status": result.status,
        }},
    )
    return result


def run_pipeline(
    raw_deals: Iterable[Dict[str, Any]],
    store_path: str | Path = DEFAULT_STORE,
    config: OnboardingConfig = DEFAULT_CONFIG,
) -> List[OnboardingResult]:
    """Process a batch of won-deal dicts. Returns the onboarding results."""
    provisioner = ProvisioningClient(store_path)
    results: List[OnboardingResult] = []
    for raw in raw_deals:
        deal = WonDeal.from_dict(raw)
        if not deal.is_valid:
            logger.warning(
                "skipping deal with missing id or unknown plan",
                extra={"context": {"raw": raw}},
            )
            continue
        results.append(process_deal(deal, provisioner, config))
    logger.info(
        "batch complete",
        extra={"context": {
            "deals_onboarded": len(results),
            "steps_provisioned_total": provisioner.count(),
        }},
    )
    return results


def main(input_path: str | Path = DEFAULT_INPUT, store_path: str | Path = DEFAULT_STORE) -> None:
    raw_deals = json.loads(Path(input_path).read_text(encoding="utf-8"))
    results = run_pipeline(raw_deals, store_path)

    steps_run = sum(len(r.completed) for r in results)
    steps_skipped = sum(len(r.skipped) for r in results)
    steps_failed = sum(len(r.failed) for r in results)

    print("\n=== Client onboarding run summary ===")
    print(f"Deals onboarded:      {len(results)}")
    print(f"Steps provisioned:    {steps_run}")
    print(f"Steps skipped (re-run): {steps_skipped}")
    if steps_failed:
        print(f"Steps failed:         {steps_failed}")

    print("\nPer deal:")
    for r in results:
        print(
            f"  {r.deal.deal_id:<10} {r.deal.plan:>10}  "
            f"{r.percent_complete:>3}%  {r.status:<18} "
            f"(+{len(r.completed)} new, {len(r.skipped)} skipped) -> {r.deal.company}"
        )

    print(f"\nOnboarding store written to: {store_path}")


if __name__ == "__main__":
    main()
