from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BenchmarkPlatformLimits(BaseModel):
    """Лимиты числа товаров по платформам в наборе (конфигурируемо по ТЗ §3.2)."""

    amazon: int = Field(default=5, ge=0)
    wayfair: int = Field(default=5, ge=0)
    walmart: int = Field(default=5, ge=0)
    yandex_market: int = Field(default=5, ge=0)


class OverallScoreWeights(BaseModel):
    """Веса композитной метрики §15 (конфигурируемые)."""

    aspect_coverage: float = Field(default=0.30, ge=0, le=1)
    sentiment_consistency: float = Field(default=0.20, ge=0, le=1)
    evidence_support_rate: float = Field(default=0.25, ge=0, le=1)
    specificity: float = Field(default=0.15, ge=0, le=1)
    non_redundancy: float = Field(default=0.10, ge=0, le=1)

    def normalized(self) -> OverallScoreWeights:
        s = (
            self.aspect_coverage
            + self.sentiment_consistency
            + self.evidence_support_rate
            + self.specificity
            + self.non_redundancy
        )
        if s <= 0:
            return self
        return OverallScoreWeights(
            aspect_coverage=self.aspect_coverage / s,
            sentiment_consistency=self.sentiment_consistency / s,
            evidence_support_rate=self.evidence_support_rate / s,
            specificity=self.specificity / s,
            non_redundancy=self.non_redundancy / s,
        )


class EvaluationRunConfig(BaseModel):
    """Параметры прогона evaluation, сериализуются в EvaluationRun.config_json."""

    benchmark_set_name: str
    method_code: str = "aspect_evidence_guided_v1"
    summarization_params: dict[str, Any] = Field(default_factory=dict)
    run_auxiliary_metrics: bool = True
    run_llm_judge: bool = True
    run_pairwise_judge: bool = True
    run_glass_box: bool = False
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    bert_score_model: str = "microsoft/deberta-v3-small"
    overall_weights: OverallScoreWeights = Field(default_factory=OverallScoreWeights)
    platform_limits: BenchmarkPlatformLimits = Field(default_factory=BenchmarkPlatformLimits)
    evidence_top_k_for_judge: int = Field(default=3, ge=1, le=20)
    claim_similarity_threshold: float = Field(default=0.55, ge=0, le=1)
    aspect_match_embedding_threshold: float = Field(default=0.72, ge=0, le=1)
