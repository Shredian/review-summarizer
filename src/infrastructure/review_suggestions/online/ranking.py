from __future__ import annotations

from src.domain.review_suggestions.entities import SuggestionCandidate, TextInputState


def score_for_field(c: SuggestionCandidate, state: TextInputState) -> SuggestionCandidate:
    ws = (c.metadata or {}).get("weak_sentiment")
    field = state.field
    rating = state.rating
    s = c.sentiment_score
    if field == "plus":
        if ws == "positive":
            s += 0.25
        if ws == "negative":
            s -= 0.2
    elif field == "minus":
        if ws == "negative":
            s += 0.25
        if ws == "positive":
            s -= 0.2
    elif field == "comment" and rating is not None:
        if rating >= 4 and ws == "positive":
            s += 0.1
        if rating <= 2 and ws == "negative":
            s += 0.1
    c.sentiment_score = max(0.0, min(1.0, s))
    return c


def rank_candidates(
    cands: list[SuggestionCandidate], state: TextInputState, max_n: int = 3
) -> list[SuggestionCandidate]:
    cands = [score_for_field(c, state) for c in cands]
    rated: list[tuple[float, SuggestionCandidate]] = []
    for c in cands:
        score = (
            0.25 * c.prefix_score
            + 0.25 * c.ngram_score
            + 0.20 * c.aspect_score
            + 0.10 * c.sentiment_score
            + 0.10 * min(1.0, c.product_frequency_score)
            + 0.05 * c.user_style_score
            + 0.05 * c.quality_score
        )
        c.confidence = max(0.0, min(1.0, score))
        rated.append((score, c))
    rated.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in rated[:max_n]]
