from src.config import DEFAULT_ICP
from src.enrichment import enrich_lead
from src.models import Lead
from src.scoring import score_lead


def _score(email, message="", company=""):
    lead = Lead(email=email, message=message, company=company)
    enrichment = enrich_lead(lead)
    return score_lead(lead, enrichment)


def test_hot_lead_business_with_intent():
    score, tier, reasons, action = _score(
        "buyer@globalsystems.com", message="need a demo and pricing, budget ready", company="Global Systems"
    )
    assert tier == "hot"
    assert score >= DEFAULT_ICP.hot_threshold
    assert action == "notify_sales_immediately"
    assert any("intent keywords" in r for r in reasons)


def test_cold_lead_free_email_no_intent():
    score, tier, _, action = _score("someone@gmail.com", message="just browsing")
    assert tier == "cold"
    assert action == "add_to_newsletter"


def test_score_is_capped_at_100():
    score, _, _, _ = _score(
        "vp@globalsystems.com",
        message="demo pricing quote buy urgent budget trial",
        company="Global Systems",
    )
    assert score <= 100


def test_intent_keywords_increase_score():
    low, *_ = _score("a@brightlabs.io", message="hello")
    high, *_ = _score("a@brightlabs.io", message="please send pricing and a demo")
    assert high > low
