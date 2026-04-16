from __future__ import annotations

from collections import Counter

from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    AspectStats,
    CanonicalAspect,
    SentimentLabel,
)


class EvidenceAggregator:
    """Собирает статистики по каноническим аспектам."""

    def aggregate(
        self,
        canonical_aspects: list[CanonicalAspect],
        reviews_count: int,
    ) -> list[AspectStats]:
        stats: list[AspectStats] = []
        for aspect in canonical_aspects:
            sentiments = Counter(mention.sentiment_label for mention in aspect.mentions)
            sections = Counter(mention.section_type.value for mention in aspect.mentions)
            source_count = len({mention.review_id for mention in aspect.mentions})
            prevalence_score = len(aspect.mentions) / max(1, reviews_count)
            polarity_balance_score = self._polarity_balance(sentiments)
            informativeness_score = min(1.0, 0.2 + len(aspect.aliases) * 0.12)
            diversity_score = min(1.0, source_count / max(1, reviews_count))

            stats.append(
                AspectStats(
                    aspect_name=aspect.canonical_name,
                    aliases=aspect.aliases,
                    total_mentions=len(aspect.mentions),
                    positive_mentions=sentiments[SentimentLabel.POSITIVE],
                    negative_mentions=sentiments[SentimentLabel.NEGATIVE],
                    neutral_mentions=sentiments[SentimentLabel.NEUTRAL],
                    mixed_mentions=sentiments[SentimentLabel.MIXED],
                    source_count=source_count,
                    review_count=source_count,
                    section_distribution=dict(sections),
                    prevalence_score=prevalence_score,
                    polarity_balance_score=polarity_balance_score,
                    informativeness_score=informativeness_score,
                    diversity_score=diversity_score,
                )
            )
        return stats

    def _polarity_balance(self, sentiments: Counter) -> float:
        positive = sentiments[SentimentLabel.POSITIVE]
        negative = sentiments[SentimentLabel.NEGATIVE]
        total = positive + negative
        if total == 0:
            return 0.0
        return 1.0 - abs(positive - negative) / total
