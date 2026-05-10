"""Датаклассы для NLP-профилей и онлайн-подсказок при наборе отзыва (без привязки к ORM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

ReviewTextField = Literal["title", "plus", "minus", "comment"]
WeakSentiment = Literal["positive", "negative", "neutral", "mixed"]
KeyphraseSource = Literal["yake", "keybert", "ngram"]
SuggestionType = Literal["next_word", "phrase_completion", "aspect_expansion", "generic_fallback"]
InsertMode = Literal["append", "replace_current_token", "replace_suffix"]
ProfileJobReason = Literal[
    "prepare_missing",
    "prepare_stale",
    "review_created",
    "manual",
]


@dataclass
class ReviewText:
    review_id: UUID
    product_id: UUID
    user_id: UUID | None
    field: ReviewTextField
    text: str
    rating: float | None
    review_date_iso: str | None


@dataclass
class ReviewSegment:
    segment_id: str
    review_id: UUID
    product_id: UUID
    user_id: UUID | None
    field: str
    raw_text: str
    normalized_text: str
    surface_tokens: list[str]
    lemmas: list[str]
    rating: float | None
    weak_sentiment: WeakSentiment


@dataclass
class KeyphraseCandidate:
    text: str
    normalized_text: str
    lemmas: list[str]
    source: KeyphraseSource
    segment_id: str
    field: str
    weak_sentiment: str
    score: float


@dataclass
class DiscoveredAspect:
    aspect_id: str
    label: str
    keywords: list[str]
    representative_phrases: list[str]
    positive_phrases: list[str]
    negative_phrases: list[str]
    neutral_phrases: list[str]
    segment_count: int
    confidence: float


@dataclass
class PhraseCandidate:
    id: str
    text: str
    normalized_text: str
    lemmas: list[str]
    aspect_id: str | None
    aspect_label: str | None
    weak_sentiment: str
    source_field: str
    frequency: int
    avg_rating: float | None
    length_tokens: int
    quality_score: float
    contains_specific_fact: bool


@dataclass
class TextInputState:
    raw_text: str
    text_before_cursor: str
    current_token: str | None
    last_surface_tokens: list[str]
    last_lemmas: list[str]
    is_empty: bool
    ends_with_space: bool
    field: str
    rating: float | None


@dataclass
class SuggestionCandidate:
    id: str
    text: str
    insert_text: str
    type: SuggestionType
    insert_mode: InsertMode
    aspect_id: str | None
    aspect_label: str | None
    confidence: float
    source: str
    prefix_score: float = 0.0
    ngram_score: float = 0.0
    aspect_score: float = 0.0
    sentiment_score: float = 0.0
    product_frequency_score: float = 0.0
    user_style_score: float = 0.0
    quality_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PreparedSuggestionContext:
    context_id: str
    product_id: UUID
    user_id: UUID | None
    rating: float | None
    field: str
    product_profile: dict[str, Any]
    user_profile: dict[str, Any] | None
    fallback_used: bool
    created_at_iso: str
