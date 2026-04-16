from __future__ import annotations

from collections import defaultdict

from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    CanonicalAspect,
    ContentPlan,
    EvidenceItem,
    SentimentLabel,
)


class EvidenceSelector:
    """Выбирает информативные и нереплицированные evidence spans."""

    def select(
        self,
        plan: ContentPlan,
        canonical_aspects: list[CanonicalAspect],
        evidence_per_aspect: int,
    ) -> list[EvidenceItem]:
        by_name = {aspect.canonical_name: aspect for aspect in canonical_aspects}
        selected_evidence: list[EvidenceItem] = []
        for planned in plan.selected_aspects:
            canonical = by_name.get(planned.aspect_name)
            if canonical is None:
                continue

            mention_groups = defaultdict(list)
            for mention in canonical.mentions:
                mention_groups[mention.review_id].append(mention)

            rank = 1
            for review_id, mentions in mention_groups.items():
                if rank > evidence_per_aspect:
                    break
                mention = self._best_mention_for_target(mentions, planned.target_polarity)
                selected_evidence.append(
                    EvidenceItem(
                        review_id=review_id,
                        aspect_name=planned.aspect_name,
                        section_type=mention.section_type,
                        evidence_text=mention.span_text,
                        polarity=mention.sentiment_label,
                        rank=rank,
                    )
                )
                rank += 1

        return selected_evidence

    def _best_mention_for_target(self, mentions: list, target_polarity: str):  # type: ignore[no-untyped-def]
        for mention in mentions:
            if target_polarity == "positive" and mention.sentiment_label == SentimentLabel.POSITIVE:
                return mention
            if target_polarity == "negative" and mention.sentiment_label == SentimentLabel.NEGATIVE:
                return mention
        return mentions[0]
