from src.classifier import classify
from src.config import DEFAULT_ROUTING
from src.models import Classification, Ticket
from src.routing import is_breaching, route, sla_deadline


def _ticket(subject="", body="", received_at="2026-06-23T10:00:00+00:00"):
    return Ticket(id="T", subject=subject, body=body, received_at=received_at)


def test_billing_routes_to_billing_queue():
    t = _ticket(subject="invoice", body="refund please on my billing")
    routed = route(t, classify(t))
    assert routed.queue == "billing-queue"
    assert routed.assignee == "billing-team"


def test_high_urgency_escalates_to_oncall():
    t = _ticket(subject="URGENT outage", body="the API is down, fix asap")
    routed = route(t, classify(t))
    assert routed.escalate is True
    assert routed.queue == DEFAULT_ROUTING.oncall_queue
    assert routed.assignee == "on-call-engineer"
    assert routed.priority == "high"


def test_general_routes_to_triage():
    t = _ticket(subject="Hi", body="just a general question with no rush")
    routed = route(t, classify(t))
    assert routed.queue == "triage-queue"


def test_sla_deadline_high_is_60_minutes():
    c = Classification(topic="technical", urgency="high", sentiment="neutral")
    assert sla_deadline(c, "2026-06-23T10:00:00+00:00") == "2026-06-23T11:00:00+00:00"


def test_sla_deadline_normal_is_480_minutes():
    c = Classification(topic="billing", urgency="normal", sentiment="neutral")
    assert sla_deadline(c, "2026-06-23T10:00:00+00:00") == "2026-06-23T18:00:00+00:00"


def test_sla_deadline_low_is_1440_minutes():
    c = Classification(topic="general", urgency="low", sentiment="neutral")
    assert sla_deadline(c, "2026-06-23T10:00:00+00:00") == "2026-06-24T10:00:00+00:00"


def test_is_breaching_true_when_past_deadline():
    t = _ticket(subject="URGENT outage", body="down asap", received_at="2026-06-23T10:30:00+00:00")
    routed = route(t, classify(t))  # high -> deadline 11:30
    assert is_breaching(routed, as_of="2026-06-23T12:00:00+00:00") is True


def test_is_breaching_false_when_before_deadline():
    t = _ticket(subject="billing", body="refund question", received_at="2026-06-23T11:45:00+00:00")
    routed = route(t, classify(t))  # normal -> deadline 19:45
    assert is_breaching(routed, as_of="2026-06-23T12:00:00+00:00") is False
