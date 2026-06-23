"""Onboarding engine.

For a won deal, computes the REQUIRED checklist steps for its plan, executes each one
idempotently through the provisioning client, and returns an OnboardingResult describing what
was completed, what was skipped (already done on a prior run), what failed, and the
percent-complete.

Rule-based so it's deterministic and testable: the required steps come straight from config,
which is exactly what an audited onboarding process needs. The same shape accepts an LLM (see
`plan_steps_with_llm` note) when you want a model to *tailor* the checklist — e.g. add a
"data_migration" step when the deal notes mention a legacy system — while these rules stay the
floor the pipeline, provisioning client, and tests all decouple from.
"""

from __future__ import annotations

from typing import List

from shared.retry import RetryError

from .config import DEFAULT_CONFIG, OnboardingConfig
from .models import OnboardingResult, WonDeal
from .provisioning_client import ProvisioningClient


def required_steps(deal: WonDeal, config: OnboardingConfig = DEFAULT_CONFIG) -> List[str]:
    """The ordered checklist a deal must complete, derived from its plan.

    LLM swap-in: replace/augment this body with a structured LLM call that returns the same
    list of step names. Keep config.steps_for(plan) as the mandatory floor and let the model
    only *append* extra steps, so onboarding is never less complete than the baseline.
    """
    return config.steps_for(deal.plan)


def onboard_deal(
    deal: WonDeal,
    provisioner: ProvisioningClient,
    config: OnboardingConfig = DEFAULT_CONFIG,
) -> OnboardingResult:
    """Run every required step for ``deal`` idempotently and return the result."""
    steps = required_steps(deal, config)
    result = OnboardingResult(deal=deal, required_steps=steps, sla_hours=config.sla_hours)

    context = {
        "company": deal.company,
        "contact_email": deal.contact_email,
        "plan": deal.plan,
        "seats": deal.seats,
        "signed_at": deal.signed_at,
    }

    for step in steps:
        try:
            newly_done = provisioner.provision(step, deal.deal_id, context)
        except RetryError:
            # Exhausted retries on a transient failure — record it and keep going so one bad
            # step doesn't strand the rest of the checklist.
            result.failed.append(step)
            continue
        if newly_done:
            result.completed.append(step)
        else:
            result.skipped.append(step)

    return result
