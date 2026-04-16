from __future__ import annotations

from collections import defaultdict

from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    ContentPlan,
    EvidenceItem,
    GenerationOutput,
    SentimentLabel,
)


class GroundedGenerator:
    """Генератор summary строго по выбранным аспектам и evidence."""

    def generate(
        self,
        plan: ContentPlan,
        evidence_items: list[EvidenceItem],
    ) -> GenerationOutput:
        by_aspect: dict[str, list[EvidenceItem]] = defaultdict(list)
        for item in evidence_items:
            by_aspect[item.aspect_name].append(item)

        pros_parts: list[str] = []
        cons_parts: list[str] = []
        neutral_parts: list[str] = []
        key_phrases: list[dict[str, str | int | float]] = []

        for planned in plan.selected_aspects:
            items = by_aspect.get(planned.aspect_name, [])
            if not items:
                continue
            supporting_snippet = "; ".join(item.evidence_text for item in items[:2])
            sentence = f"{planned.aspect_name}: {supporting_snippet}"
            polarity_set = {item.polarity for item in items}

            if polarity_set == {SentimentLabel.POSITIVE}:
                pros_parts.append(sentence)
            elif polarity_set == {SentimentLabel.NEGATIVE}:
                cons_parts.append(sentence)
            else:
                neutral_parts.append(sentence)

            key_phrases.append(
                {
                    "phrase": planned.aspect_name,
                    "sentiment": planned.target_polarity,
                    "count": len(items),
                    "share": round(min(1.0, len(items) / max(1, len(evidence_items))), 2),
                }
            )

        overall_parts: list[str] = []
        if pros_parts:
            overall_parts.append("Сильные стороны: " + " | ".join(pros_parts))
        if cons_parts:
            overall_parts.append("Слабые стороны: " + " | ".join(cons_parts))
        if neutral_parts:
            overall_parts.append("Смешанные наблюдения: " + " | ".join(neutral_parts))

        return GenerationOutput(
            text_overall="\n".join(overall_parts) if overall_parts else None,
            text_pros="\n".join(pros_parts) if pros_parts else None,
            text_cons="\n".join(cons_parts) if cons_parts else None,
            text_neutral="\n".join(neutral_parts) if neutral_parts else None,
            key_phrases=key_phrases,
        )
