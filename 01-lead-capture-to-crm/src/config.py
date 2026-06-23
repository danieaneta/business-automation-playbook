"""Ideal Customer Profile (ICP) config + scoring weights.

In a real deployment these live in environment variables / a config file so non-engineers can
tune the ICP without touching code. See `.env.example` for the production-integration knobs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class ICPConfig:
    """Defines what a "good" lead looks like and how each signal is weighted."""

    # Intent keywords found in the lead's message bump the score.
    intent_keywords: List[str] = field(
        default_factory=lambda: ["pricing", "demo", "quote", "buy", "urgent", "budget", "trial"]
    )
    # Company sizes we sell best to, mapped to points.
    size_points: Dict[str, int] = field(
        default_factory=lambda: {"smb": 15, "mid": 30, "enterprise": 40}
    )
    # Free/personal email domains score lower (less likely a qualified business lead).
    free_email_domains: List[str] = field(
        default_factory=lambda: ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"]
    )

    points_business_domain: int = 25
    points_per_intent_keyword: int = 10
    points_named_company: int = 10
    points_has_message: int = 5

    # Score thresholds → tier → follow-up action.
    hot_threshold: int = 60
    warm_threshold: int = 35

    def tier_for(self, score: int) -> str:
        if score >= self.hot_threshold:
            return "hot"
        if score >= self.warm_threshold:
            return "warm"
        return "cold"

    def action_for(self, tier: str) -> str:
        return {
            "hot": "notify_sales_immediately",
            "warm": "send_nurture_sequence",
            "cold": "add_to_newsletter",
        }[tier]


DEFAULT_ICP = ICPConfig()
