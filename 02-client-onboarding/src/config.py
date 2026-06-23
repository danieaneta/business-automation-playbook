"""Onboarding checklist config — the ordered steps, per-plan variation, and SLA.

In a real deployment these live in environment variables / a config file so ops can change the
checklist without touching code. See `.env.example` for the production-integration knobs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

# The base post-sale checklist, in execution order. Every won deal gets these.
BASE_STEPS: List[str] = [
    "provision_account",
    "create_workspace",
    "add_to_billing",
    "send_welcome_email",
    "schedule_kickoff",
]

# Extra steps a given plan adds, appended in order after the base checklist.
PLAN_EXTRA_STEPS: Dict[str, List[str]] = {
    "smb": [],
    "pro": [],
    "enterprise": ["assign_csm"],  # enterprise customers get a dedicated CSM.
}


@dataclass(frozen=True)
class OnboardingConfig:
    """Defines the onboarding checklist, its per-plan variations, and the SLA."""

    base_steps: List[str] = field(default_factory=lambda: list(BASE_STEPS))
    plan_extra_steps: Dict[str, List[str]] = field(
        default_factory=lambda: {k: list(v) for k, v in PLAN_EXTRA_STEPS.items()}
    )
    # How long (hours) onboarding should take from signed_at before it breaches SLA.
    sla_hours: int = 48

    def steps_for(self, plan: str) -> List[str]:
        """Return the ordered, de-duplicated list of required steps for a plan.

        Order is preserved (base steps first, then plan extras). An unknown plan falls back to
        the base checklist only, so a typo never silently drops the whole onboarding.
        """
        steps = list(self.base_steps)
        for extra in self.plan_extra_steps.get(plan, []):
            if extra not in steps:
                steps.append(extra)
        return steps


DEFAULT_CONFIG = OnboardingConfig()
