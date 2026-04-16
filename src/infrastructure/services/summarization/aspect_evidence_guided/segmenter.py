import re
from typing import Iterable

from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    NormalizedReview,
    ReviewSpan,
    SectionType,
)

try:
    import spacy
except ImportError:  # pragma: no cover - optional runtime dependency
    spacy = None


class SpanSegmenter:
    """Сегментирует канонический отзыв в sentence/spans."""

    def __init__(self, max_spans_per_review: int = 30) -> None:
        self._max_spans_per_review = max_spans_per_review
        self._nlp = self._build_nlp()

    def _build_nlp(self):  # type: ignore[no-untyped-def]
        if spacy is None:
            return None
        try:
            return spacy.load("ru_core_news_sm")
        except Exception:
            nlp = spacy.blank("ru")
            nlp.add_pipe("sentencizer")
            return nlp

    def segment(self, normalized_reviews: Iterable[NormalizedReview]) -> list[ReviewSpan]:
        spans: list[ReviewSpan] = []
        for normalized_review in normalized_reviews:
            current_index = 0
            for chunk in normalized_review.sections:
                if current_index >= self._max_spans_per_review:
                    break
                chunk_spans = self._split_text(chunk.text)
                for span_text in chunk_spans:
                    cleaned = span_text.strip()
                    if len(cleaned) < 3:
                        continue
                    spans.append(
                        ReviewSpan(
                            review_id=normalized_review.review_id,
                            product_id=normalized_review.product_id,
                            source=normalized_review.source,
                            section_type=SectionType(chunk.section),
                            span_text=cleaned,
                            normalized_text=cleaned.lower(),
                            span_index=current_index,
                        )
                    )
                    current_index += 1
                    if current_index >= self._max_spans_per_review:
                        break
        return spans

    def _split_text(self, text: str) -> list[str]:
        if self._nlp is None:
            parts = re.split(r"[.!?;\n]+", text)
            return [part.strip() for part in parts if part.strip()]

        doc = self._nlp(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
