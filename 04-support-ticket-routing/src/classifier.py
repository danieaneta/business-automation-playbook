"""Ticket classification.

Turns a raw ticket into a Classification (topic, urgency, sentiment) with the reasons behind
each call. Rule-based so it's deterministic and testable — the same `classify(ticket)` shape
accepts an LLM verdict when you want nuance.

LLM swap-in (this is the realistic place an LLM slots in):
    Replace the body of `classify` with a structured call to `claude-opus-4-8` that returns the
    same Classification dataclass (topic from a fixed enum, urgency in {high,normal,low},
    sentiment in {negative,neutral}). Keep these rules as a deterministic fallback for when the
    model is unavailable or rate-limited. The pipeline, routing, SLA, and tests are all
    decoupled from HOW the verdict is produced — see `.env.example` (ANTHROPIC_API_KEY /
    CLASSIFIER_MODEL=claude-opus-4-8).
"""

from __future__ import annotations

from typing import List

from .config import DEFAULT_ROUTING, RoutingConfig
from .models import Classification, Ticket


def _best_topic(text: str, cfg: RoutingConfig) -> tuple[str, int, List[str]]:
    """Return (topic, hit_count, matched_keywords). Falls back to 'general' on no match."""
    best_topic = "general"
    best_hits: List[str] = []
    # Iterate in config order so ties resolve deterministically to the first-declared topic.
    for topic, keywords in cfg.topic_keywords.items():
        hits = [kw for kw in keywords if kw in text]
        if len(hits) > len(best_hits):
            best_topic, best_hits = topic, hits
    return best_topic, len(best_hits), best_hits


def _urgency(text: str, cfg: RoutingConfig) -> tuple[str, List[str]]:
    """High signals win over low signals; default is normal."""
    high = [s for s in cfg.high_urgency_signals if s in text]
    if high:
        return "high", high
    low = [s for s in cfg.low_urgency_signals if s in text]
    if low:
        return "low", low
    return "normal", []


def _sentiment(text: str, cfg: RoutingConfig) -> tuple[str, List[str]]:
    hits = [s for s in cfg.negative_signals if s in text]
    return ("negative" if hits else "neutral"), hits


def classify(ticket: Ticket, cfg: RoutingConfig = DEFAULT_ROUTING) -> Classification:
    """Classify a ticket into topic, urgency, and sentiment with explainable reasons."""
    text = ticket.text
    reasons: List[str] = []

    topic, hit_count, topic_hits = _best_topic(text, cfg)
    if topic == "general":
        reasons.append("no topic keywords matched -> general")
    else:
        reasons.append(f"topic '{topic}' from keywords {topic_hits}")

    urgency, urgency_hits = _urgency(text, cfg)
    if urgency == "high":
        reasons.append(f"high urgency from signals {urgency_hits}")
    elif urgency == "low":
        reasons.append(f"low urgency from signals {urgency_hits}")
    else:
        reasons.append("normal urgency (no urgency signals)")

    sentiment, sentiment_hits = _sentiment(text, cfg)
    if sentiment == "negative":
        reasons.append(f"negative sentiment from {sentiment_hits}")

    return Classification(topic=topic, urgency=urgency, sentiment=sentiment, reasons=reasons)
