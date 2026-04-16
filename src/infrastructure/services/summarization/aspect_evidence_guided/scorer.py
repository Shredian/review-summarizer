from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    AspectEvidenceGuidedParams,
    AspectStats,
)


class AspectScorer:
    """Configurable scoring для выбора аспектов."""

    def score(
        self,
        aspect_stats: list[AspectStats],
        params: AspectEvidenceGuidedParams,
    ) -> list[AspectStats]:
        for stat in aspect_stats:
            rarity_flag = stat.prevalence_score <= params.rarity_share_threshold
            rarity_bonus = params.rarity_bonus if rarity_flag else 0.0
            importance_score = (
                stat.prevalence_score * params.prevalence_weight
                + stat.polarity_balance_score * params.polarity_weight
                + stat.informativeness_score * params.informativeness_weight
                + stat.diversity_score * params.diversity_weight
                + rarity_bonus
            )
            stat.rarity_flag = rarity_flag
            stat.importance_score = round(importance_score, 6)

        return sorted(aspect_stats, key=lambda item: item.importance_score, reverse=True)
