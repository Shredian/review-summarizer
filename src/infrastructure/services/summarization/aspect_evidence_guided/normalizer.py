from typing import Iterable

from src.domain.models.review import Review
from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    NormalizedReview,
    SectionChunk,
    SectionType,
)


class ReviewNormalizer:
    """Собирает канонический текст отзыва с секционными маркерами."""

    _SECTION_MARKERS: dict[SectionType, str] = {
        SectionType.TITLE: "[TITLE]",
        SectionType.PLUS: "[PLUS]",
        SectionType.MINUS: "[MINUS]",
        SectionType.COMMENT: "[COMMENT]",
    }

    def normalize(self, reviews: Iterable[Review]) -> list[NormalizedReview]:
        normalized_reviews: list[NormalizedReview] = []

        for review in reviews:
            if review.id is None:
                continue
            sections: list[SectionChunk] = []
            if review.title:
                sections.append(SectionChunk(section=SectionType.TITLE, text=review.title.strip()))
            if review.plus:
                sections.append(SectionChunk(section=SectionType.PLUS, text=review.plus.strip()))
            if review.minus:
                sections.append(SectionChunk(section=SectionType.MINUS, text=review.minus.strip()))
            if review.comment:
                sections.append(SectionChunk(section=SectionType.COMMENT, text=review.comment.strip()))

            if not sections:
                continue

            canonical_parts = [
                f"{self._SECTION_MARKERS[chunk.section]} {chunk.text}" for chunk in sections
            ]
            normalized_reviews.append(
                NormalizedReview(
                    review_id=review.id,
                    product_id=review.product_id,
                    source=review.source,
                    sections=sections,
                    canonical_text="\n".join(canonical_parts),
                )
            )

        return normalized_reviews
