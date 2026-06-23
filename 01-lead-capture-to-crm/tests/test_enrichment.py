from src.enrichment import enrich_lead
from src.models import Lead


def test_free_email_is_not_business():
    e = enrich_lead(Lead(email="x@gmail.com"))
    assert e["is_business_email"] is False


def test_business_email_is_detected():
    e = enrich_lead(Lead(email="x@acme-industries.com"))
    assert e["is_business_email"] is True
    assert e["company_guess"] == "Acme Industries"


def test_enterprise_hint_sizes_up():
    e = enrich_lead(Lead(email="x@globalsystems.com"))
    assert e["company_size"] == "enterprise"


def test_malformed_email_has_empty_domain():
    e = enrich_lead(Lead(email="not-an-email"))
    assert e["domain"] == ""
    assert e["is_business_email"] is False
