"""Сбор текстов отзывов для пайплайна профиля (отдельные поля без склейки)."""

from __future__ import annotations

from src.domain.models.review import Review
from src.domain.review_suggestions.entities import ReviewText


def collect_review_texts_from_reviews(reviews: list[Review]) -> list[ReviewText]:
    out: list[ReviewText] = []
    for r in reviews:
        if r.id is None:
            continue
        uid = r.user_id
        rd = r.review_date.isoformat() if r.review_date else None
        if r.title and r.title.strip():
            out.append(
                ReviewText(
                    review_id=r.id,
                    product_id=r.product_id,
                    user_id=uid,
                    field="title",
                    text=r.title.strip(),
                    rating=r.rating,
                    review_date_iso=rd,
                )
            )
        if r.plus and r.plus.strip():
            out.append(
                ReviewText(
                    review_id=r.id,
                    product_id=r.product_id,
                    user_id=uid,
                    field="plus",
                    text=r.plus.strip(),
                    rating=r.rating,
                    review_date_iso=rd,
                )
            )
        if r.minus and r.minus.strip():
            out.append(
                ReviewText(
                    review_id=r.id,
                    product_id=r.product_id,
                    user_id=uid,
                    field="minus",
                    text=r.minus.strip(),
                    rating=r.rating,
                    review_date_iso=rd,
                )
            )
        if r.comment and r.comment.strip():
            out.append(
                ReviewText(
                    review_id=r.id,
                    product_id=r.product_id,
                    user_id=uid,
                    field="comment",
                    text=r.comment.strip(),
                    rating=r.rating,
                    review_date_iso=rd,
                )
            )
    return out


def weak_sentiment_for_field(field: str, rating: float | None) -> str:
    if field == "plus":
        return "positive"
    if field == "minus":
        return "negative"
    if field == "comment":
        if rating is not None and rating >= 4:
            return "positive"
        if rating is not None and rating <= 2:
            return "negative"
        if rating is not None and abs(rating - 3) < 0.25:
            return "mixed"
    return "neutral"
