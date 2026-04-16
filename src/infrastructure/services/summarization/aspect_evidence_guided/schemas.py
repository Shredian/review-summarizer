from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class SectionType(StrEnum):
    TITLE = "title"
    PLUS = "plus"
    MINUS = "minus"
    COMMENT = "comment"


class SentimentLabel(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


@dataclass(frozen=True)
class SectionChunk:
    section: SectionType
    text: str


class NormalizedReview(BaseModel):
    review_id: UUID
    product_id: UUID
    source: str
    sections: list[SectionChunk]
    canonical_text: str


class ReviewSpan(BaseModel):
    review_id: UUID
    product_id: UUID
    source: str
    section_type: SectionType
    span_text: str
    normalized_text: str
    span_index: int


class MentionExtractionResult(BaseModel):
    review_id: UUID
    section_type: SectionType
    span_text: str
    aspect_raw: str
    aspect_candidate: str
    sentiment_label: SentimentLabel
    sentiment_score: float | None = None
    extractor_confidence: float | None = None


class CanonicalAspect(BaseModel):
    canonical_name: str
    aliases: list[str]
    mentions: list[MentionExtractionResult]


class AspectStats(BaseModel):
    aspect_name: str
    aliases: list[str]
    total_mentions: int
    positive_mentions: int
    negative_mentions: int
    neutral_mentions: int
    mixed_mentions: int
    source_count: int
    review_count: int
    section_distribution: dict[str, int]
    rarity_flag: bool = False
    prevalence_score: float = 0.0
    polarity_balance_score: float = 0.0
    informativeness_score: float = 0.0
    diversity_score: float = 0.0
    importance_score: float = 0.0


class EvidenceItem(BaseModel):
    review_id: UUID
    aspect_name: str
    section_type: SectionType
    evidence_text: str
    polarity: SentimentLabel
    rank: int


class PlannedAspect(BaseModel):
    aspect_name: str
    target_polarity: Literal["positive", "negative", "balanced", "neutral"]
    importance_score: float
    rarity_flag: bool
    expected_mentions: int


class ContentPlan(BaseModel):
    selected_aspects: list[PlannedAspect]
    dropped_aspects: list[str]
    diagnostics: dict[str, Any]


class GenerationOutput(BaseModel):
    text_overall: str | None = None
    text_pros: str | None = None
    text_cons: str | None = None
    text_neutral: str | None = None
    key_phrases: list[dict[str, Any]] = Field(default_factory=list)


class VerificationResult(BaseModel):
    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    revised_output: GenerationOutput | None = None


class AspectEvidenceGuidedParams(BaseModel):
    """Параметры `aspect_evidence_guided_v1`.

    Максимальное качество: `enable_keybert_refinement` и `enable_llm_refinement`, ключ OpenAI в окружении;
    для KeyBERT и кластеризации нужны зависимости из `requirements.research.txt` (в Docker включаются по умолчанию).
    """

    category: str = "товар"
    max_spans_per_review: int = Field(default=30, ge=3, le=200)
    min_candidate_len: int = Field(default=3, ge=2, le=50)
    max_candidates: int = Field(default=120, ge=10, le=1000)
    max_selected_aspects: int = Field(default=8, ge=3, le=30)
    min_selected_aspects: int = Field(default=5, ge=2, le=20)
    evidence_per_aspect: int = Field(default=3, ge=1, le=10)
    minority_aspect_min_mentions: int = Field(default=2, ge=1, le=30)
    rarity_share_threshold: float = Field(default=0.08, ge=0.01, le=0.5)
    prevalence_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    polarity_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    informativeness_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    diversity_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    rarity_bonus: float = Field(default=0.15, ge=0.0, le=1.0)
    # Одна мультиязычная модель для KeyBERT и кластеризации аспектов (sentence-transformers).
    embedding_model_name: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        min_length=3,
        max_length=256,
    )
    enable_keybert_refinement: bool = False
    enable_llm_refinement: bool = False
    llm_overall_sentences: int = Field(default=5, ge=2, le=12)

    def to_reproducible_params(self) -> dict[str, Any]:
        return self.model_dump()


# ---------------------------------------------------------------------------
# DTO для передачи данных в LLM-генерацию (не зависят от ORM)
# ---------------------------------------------------------------------------


class EvidenceInput(BaseModel):
    """Единица evidence для передачи в LLM."""

    text: str
    section_type: SectionType
    sentiment_label: SentimentLabel
    evidence_score: float = 0.0


class AspectSummaryInput(BaseModel):
    """Агрегированные данные по одному аспекту для LLM-генерации."""

    aspect_name: str
    importance_score: float
    prevalence_score: float
    total_mentions: int
    positive_mentions: int
    negative_mentions: int
    neutral_mentions: int
    target_polarity: str
    rarity_flag: bool
    must_include: bool
    aliases: list[str] = Field(default_factory=list)
    representative_evidence: list[EvidenceInput] = Field(default_factory=list)


class GenerationConstraints(BaseModel):
    """Ограничения и стиль генерации."""

    style: str = "neutral analytical"
    max_sentences: int = 5
    preserve_balance: bool = True
    no_unsupported_claims: bool = True
    category: str = "товар"


class SummaryGenerationInput(BaseModel):
    """Полный structured context для LLM-генерации summary."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    product_id: UUID
    reviews_count: int
    rating_avg: float | None
    selected_aspects: list[AspectSummaryInput]
    generation_constraints: GenerationConstraints


# ---------------------------------------------------------------------------
# Structured output schemas для LLM (используются с with_structured_output)
# ---------------------------------------------------------------------------


class LLMOverallOutput(BaseModel):
    """JSON-схема ответа LLM для text_overall."""

    text_overall: str


class LLMProsOutput(BaseModel):
    """JSON-схема ответа LLM для text_pros."""

    text_pros: str


class LLMConsOutput(BaseModel):
    """JSON-схема ответа LLM для text_cons."""

    text_cons: str


class LLMVerificationOutput(BaseModel):
    """JSON-схема ответа LLM-верификатора."""

    is_valid: bool
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_aspects: list[str] = Field(default_factory=list)
    polarity_issues: list[str] = Field(default_factory=list)
    revision_instructions: str | None = None
