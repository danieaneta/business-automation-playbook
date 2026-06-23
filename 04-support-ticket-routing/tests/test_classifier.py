from src.classifier import classify
from src.models import Ticket


def _classify(subject="", body=""):
    return classify(Ticket(id="T", subject=subject, body=body, received_at="2026-06-23T10:00:00+00:00"))


def test_billing_topic_detected():
    c = _classify(subject="invoice problem", body="I was double charged, need a refund")
    assert c.topic == "billing"


def test_technical_topic_detected():
    c = _classify(subject="App crash", body="I keep getting a 500 error and the page is broken")
    assert c.topic == "technical"


def test_account_topic_detected():
    c = _classify(subject="Password reset", body="My account is locked and I can't reset access")
    assert c.topic == "account"


def test_sales_topic_detected():
    c = _classify(subject="Demo request", body="We want a demo and a quote to upgrade our plan")
    assert c.topic == "sales"


def test_unknown_topic_falls_back_to_general():
    c = _classify(subject="Hello", body="Just saying hi, nothing specific")
    assert c.topic == "general"


def test_high_urgency_detected_from_signals():
    c = _classify(subject="URGENT outage", body="The system is down, fix asap")
    assert c.urgency == "high"


def test_low_urgency_detected_from_signals():
    c = _classify(subject="Minor idea", body="No rush at all, whenever you get a chance")
    assert c.urgency == "low"


def test_default_urgency_is_normal():
    c = _classify(subject="Quick question", body="How do I export my data?")
    assert c.urgency == "normal"


def test_negative_sentiment_flagged_on_complaint_words():
    c = _classify(subject="Awful", body="This is unacceptable and I am furious")
    assert c.sentiment == "negative"


def test_neutral_sentiment_by_default():
    c = _classify(subject="Question", body="Could you tell me how billing works?")
    assert c.sentiment == "neutral"
