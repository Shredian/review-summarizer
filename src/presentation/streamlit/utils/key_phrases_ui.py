"""Группировка ключевых фраз для отображения в Streamlit."""

from __future__ import annotations


def normalize_key_phrase_sentiment(raw: str | None) -> str | None:
    s = (raw or "").strip().lower()
    if s in ("positive", "pos", "+", "plus"):
        return "positive"
    if s in ("negative", "neg", "-", "minus"):
        return "negative"
    if s in ("neutral", "neu", "balanced", "mixed"):
        return "neutral"
    return None


def bucket_key_phrases(
    key_phrases: list,
) -> tuple[list, list, list, list]:
    positive: list = []
    negative: list = []
    neutral: list = []
    other: list = []
    for kp in key_phrases:
        norm = normalize_key_phrase_sentiment(getattr(kp, "sentiment", None))
        if norm == "positive":
            positive.append(kp)
        elif norm == "negative":
            negative.append(kp)
        elif norm == "neutral":
            neutral.append(kp)
        else:
            other.append(kp)
    return positive, negative, neutral, other
