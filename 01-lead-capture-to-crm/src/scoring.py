"""ICP scoring.

Turns a lead + its enrichment into a 0–100-ish score, a tier (hot/warm/cold), the reasons
behind the score, and the follow-up action. Rule-based so it's deterministic and testable; the
same shape accepts an LLM score (see `score_with_llm` note) when you want nuance.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .config import DEFAULT_ICP, ICPConfig
from .models import Lead


def score_lead(
    lead: Lead, enrichment: Dict[str, Any], icp: ICPConfig = DEFAULT_ICP
) -> Tuple[int, str, List[str], str]:
    """Return (score, tier, reasons, next_action) for a lead.

    LLM swap-in: replace this body with a structured LLM call that returns the same tuple, or
    blend — keep these rules as a floor and let the model adjust within a band. The pipeline,
    CRM write, and tests are all decoupled from how the number is produced.
    """
    score = 0
    reasons: List[str] = []

    if enrichment.get("is_business_email"):
        score += icp.points_business_domain
        reasons.append(f"business email (+{icp.points_business_domain})")

    size = enrichment.get("company_size", "smb")
    size_pts = icp.size_points.get(size, 0)
    if size_pts:
        score += size_pts
        reasons.append(f"company size '{size}' (+{size_pts})")

    msg = lead.message.lower()
    hits = [kw for kw in icp.intent_keywords if kw in msg]
    if hits:
        pts = len(hits) * icp.points_per_intent_keyword
        score += pts
        reasons.append(f"intent keywords {hits} (+{pts})")

    if lead.company:
        score += icp.points_named_company
        reasons.append(f"named company (+{icp.points_named_company})")

    if lead.message:
        score += icp.points_has_message
        reasons.append(f"left a message (+{icp.points_has_message})")

    score = min(score, 100)
    tier = icp.tier_for(score)
    action = icp.action_for(tier)
    return score, tier, reasons, action
