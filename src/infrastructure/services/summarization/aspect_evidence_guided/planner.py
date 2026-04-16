from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    AspectEvidenceGuidedParams,
    AspectStats,
    ContentPlan,
    PlannedAspect,
)


class ContentPlanner:
    """Планирует покрытие аспектов и баланс полярностей."""

    def build_plan(
        self,
        scored_aspects: list[AspectStats],
        params: AspectEvidenceGuidedParams,
    ) -> ContentPlan:
        max_selected = min(params.max_selected_aspects, len(scored_aspects))
        min_selected = min(params.min_selected_aspects, max_selected)
        selected = scored_aspects[:max_selected]

        if len(selected) < min_selected:
            selected = scored_aspects[:min_selected]

        selected_aspects: list[PlannedAspect] = []
        for stat in selected:
            target_polarity = self._target_polarity(stat)
            selected_aspects.append(
                PlannedAspect(
                    aspect_name=stat.aspect_name,
                    target_polarity=target_polarity,
                    importance_score=stat.importance_score,
                    rarity_flag=stat.rarity_flag,
                    expected_mentions=stat.total_mentions,
                )
            )

        dropped = [stat.aspect_name for stat in scored_aspects[max_selected:]]
        diagnostics = {
            "selected_count": len(selected_aspects),
            "dropped_count": len(dropped),
            "rare_selected": len([item for item in selected_aspects if item.rarity_flag]),
            "mean_importance": round(
                sum(item.importance_score for item in selected_aspects) / max(1, len(selected_aspects)),
                6,
            ),
        }
        return ContentPlan(
            selected_aspects=selected_aspects,
            dropped_aspects=dropped,
            diagnostics=diagnostics,
        )

    def _target_polarity(self, stat: AspectStats) -> str:
        if stat.positive_mentions > stat.negative_mentions:
            return "positive"
        if stat.negative_mentions > stat.positive_mentions:
            return "negative"
        if stat.neutral_mentions >= max(stat.positive_mentions, stat.negative_mentions):
            return "neutral"
        return "balanced"
