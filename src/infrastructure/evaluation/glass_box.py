from __future__ import annotations

from typing import Any

from src.domain.evaluation.dto import MetricResultDTO
from src.infrastructure.evaluation.metrics.primary import flatten_summary_text, split_claims
from src.infrastructure.db.models.summary_plan import SummaryPlanDB


def glass_box_from_plan(
    plan: SummaryPlanDB | None,
    summary: dict[str, Any],
) -> list[MetricResultDTO]:
    """Диагностика content plan vs итоговый текст (§12.4)."""
    if plan is None:
        return [
            MetricResultDTO(
                metric_name="glass_plan_reflection_rate",
                value=None,
                details_json={"skipped": "no_plan"},
            )
        ]
    items = plan.selected_aspects_json.get("items", [])
    if not isinstance(items, list):
        items = []
    names = []
    for it in items:
        if isinstance(it, dict) and it.get("aspect_name"):
            names.append(str(it["aspect_name"]))
    flat = flatten_summary_text(summary).lower()
    reflected = sum(1 for n in names if n.lower() in flat)
    rate = reflected / max(len(names), 1)

    claims = split_claims(flat)
    plan_keyword_hits = 0
    for c in claims:
        if any(n.lower() in c for n in names):
            plan_keyword_hits += 1
    claim_align = plan_keyword_hits / max(len(claims), 1)

    return [
        MetricResultDTO(
            metric_name="glass_plan_reflection_rate",
            value=float(rate),
            details_json={"planned_aspects": len(names), "reflected": reflected},
        ),
        MetricResultDTO(
            metric_name="glass_claim_aspect_overlap",
            value=float(claim_align),
            details_json={"claims": len(claims)},
        ),
    ]
