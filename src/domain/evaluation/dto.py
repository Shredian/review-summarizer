from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ReferenceEvidenceDTO(BaseModel):
    review_id: UUID
    text: str
    section_type: str
    polarity: str
    evidence_strength: float | None = None


class ReferenceAspectDTO(BaseModel):
    aspect_name: str
    aliases: list[str] = Field(default_factory=list)
    salience_weight: float = 1.0
    expected_polarity: str
    polarity_distribution: dict[str, float] | None = None
    rare_but_important: bool = False
    evidence_items: list[ReferenceEvidenceDTO] = Field(default_factory=list)


class EvaluationBenchmarkItem(BaseModel):
    """Единый элемент набора для расчёта метрик в памяти."""

    product_id: UUID
    platform_name: str
    product_title: str
    reviews: list[dict[str, Any]] = Field(default_factory=list)
    external_summary: dict[str, Any] = Field(default_factory=dict)
    our_summary: dict[str, Any] = Field(default_factory=dict)
    snapshot_timestamp: datetime | None = None
    reference_aspects: list[ReferenceAspectDTO] = Field(default_factory=list)


class ClaimDTO(BaseModel):
    text: str
    linked_aspect: str | None = None
    predicted_polarity: str | None = None


class MetricResultDTO(BaseModel):
    metric_name: str
    value: float | None
    details_json: dict[str, Any] = Field(default_factory=dict)


class JudgeRubricScoresDTO(BaseModel):
    faithfulness_score: float | None = None
    coverage_score: float | None = None
    sentiment_consistency_score: float | None = None
    specificity_score: float | None = None
    overall_preference: float | None = None
    rationale: str | None = None
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_aspects: list[str] = Field(default_factory=list)


class JudgePairwiseScoresDTO(BaseModel):
    """Структурированный выход pairwise §11.3–11.4."""

    faithfulness_score: float | None = None
    coverage_score: float | None = None
    sentiment_consistency_score: float | None = None
    specificity_score: float | None = None
    overall_preference: float | None = None
    winner: str | None = Field(
        default=None,
        description="our_method | external | tie",
    )
    rationale: str | None = None
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_aspects: list[str] = Field(default_factory=list)


class SystemEvaluationDTO(BaseModel):
    system_name: str
    product_id: UUID
    metric_results: list[MetricResultDTO] = Field(default_factory=list)
    judge_results: dict[str, Any] | None = None
    notes: dict[str, Any] | None = None


class ComparisonReportDTO(BaseModel):
    benchmark_name: str
    systems: list[str] = Field(default_factory=list)
    table_rows: list[dict[str, Any]] = Field(default_factory=list)
    aggregate_scores: dict[str, Any] = Field(default_factory=dict)
    chart_paths: list[str] = Field(default_factory=list)
