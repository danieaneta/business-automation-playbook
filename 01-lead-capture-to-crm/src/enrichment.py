"""Lead enrichment.

In production this calls an enrichment API (Clearbit, Apollo, etc.) behind the shared retry
wrapper. For a runnable, key-free demo it infers firmographics from the email domain. The
function signature is what a real provider call would look like, so swapping in HTTP is a
one-function change.
"""

from __future__ import annotations

from typing import Any, Dict

from .config import DEFAULT_ICP, ICPConfig
from .models import Lead

# Toy heuristic mapping so the demo produces varied, realistic-looking output without a network.
_SIZE_BY_DOMAIN_HINT = {
    "enterprise": ["corp", "global", "group", "industries", "systems"],
    "mid": ["labs", "tech", "software", "digital", "media"],
}


def enrich_lead(lead: Lead, icp: ICPConfig = DEFAULT_ICP) -> Dict[str, Any]:
    """Return firmographic enrichment for a lead.

    Real swap-in: wrap an Apollo/Clearbit call with ``@retry(...)`` and return its payload.
    """
    domain = lead.domain
    is_free = domain in icp.free_email_domains
    is_business = bool(domain) and not is_free

    size = "smb"
    if is_business:
        for candidate, hints in _SIZE_BY_DOMAIN_HINT.items():
            if any(h in domain for h in hints):
                size = candidate
                break
        else:
            size = "mid" if domain.endswith(".io") else "smb"

    company_guess = lead.company
    if not company_guess and is_business:
        company_guess = domain.split(".", 1)[0].replace("-", " ").title()

    return {
        "domain": domain,
        "is_business_email": is_business,
        "company_size": size,
        "company_guess": company_guess,
    }
