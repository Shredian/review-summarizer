from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from loguru import logger

from src.domain.models.review import Review
from src.domain.models.summary import KeyPhraseItem, Summary
from src.infrastructure.clients.openai_client import OpenAIClient
from src.infrastructure.db.models.aspect_cluster import AspectClusterDB
from src.infrastructure.db.models.aspect_mention import AspectMentionDB
from src.infrastructure.db.models.summary_evidence import SummaryEvidenceDB
from src.infrastructure.db.models.summary_plan import SummaryPlanDB
from src.infrastructure.db.repositories.aspect_cluster_repository import AspectClusterRepository
from src.infrastructure.db.repositories.aspect_mention_repository import AspectMentionRepository
from src.infrastructure.db.repositories.summary_evidence_repository import SummaryEvidenceRepository
from src.infrastructure.db.repositories.summary_plan_repository import SummaryPlanRepository
from src.infrastructure.services.summarization.aspect_evidence_guided.aggregator import (
    EvidenceAggregator,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.aspect_candidates import (
    AspectCandidateGenerator,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.canonicalizer import (
    AspectCanonicalizer,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.evidence_selector import (
    EvidenceSelector,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.grounded_generator import (
    GroundedGenerator,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.llm_generator import (
    LLMGroundedGenerator,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.llm_verifier import (
    LLMSummaryVerifier,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.mention_extractor import (
    HeuristicMentionExtractor,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.normalizer import (
    ReviewNormalizer,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.planner import ContentPlanner
from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    AspectEvidenceGuidedParams,
    AspectStats,
    AspectSummaryInput,
    ContentPlan,
    EvidenceInput,
    EvidenceItem,
    GenerationConstraints,
    SummaryGenerationInput,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.scorer import AspectScorer
from src.infrastructure.services.summarization.aspect_evidence_guided.segmenter import SpanSegmenter
from src.infrastructure.services.summarization.aspect_evidence_guided.verifier import SummaryVerifier
from src.infrastructure.services.summarization.base import BaseSummarizationMethod


@dataclass
class PendingArtifacts:
    product_id: UUID
    mentions: list[Any]
    scored_aspects: list[AspectStats]
    plan: Any
    evidence_items: list[Any]
    extractor_version: str


class AspectEvidenceGuidedSummarizationMethod(BaseSummarizationMethod):
    """Aspect-guided evidence-grounded метод суммаризации."""

    PIPELINE_VERSION = "aeg_v1.0.0"
    PLANNER_VERSION = "planner_v1"

    def __init__(
        self,
        aspect_mention_repository: AspectMentionRepository,
        aspect_cluster_repository: AspectClusterRepository,
        summary_evidence_repository: SummaryEvidenceRepository,
        summary_plan_repository: SummaryPlanRepository,
        openai_client: OpenAIClient | None = None,
    ) -> None:
        self._aspect_mention_repository = aspect_mention_repository
        self._aspect_cluster_repository = aspect_cluster_repository
        self._summary_evidence_repository = summary_evidence_repository
        self._summary_plan_repository = summary_plan_repository
        self._openai_client = openai_client
        self._pending_artifacts: dict[UUID, PendingArtifacts] = {}
        self._pending_lock = asyncio.Lock()

    @property
    def code(self) -> str:
        return "aspect_evidence_guided_v1"

    @property
    def name(self) -> str:
        return "Aspect Evidence Guided Summarization"

    @property
    def version(self) -> str:
        return self.PIPELINE_VERSION

    @property
    def description(self) -> str:
        return (
            "Aspect-guided, evidence-grounded, coverage-controlled pipeline "
            "с верификацией и сохранением промежуточных артефактов."
        )

    async def summarize(
        self,
        product_id: str,
        reviews: list[Review],
        params: dict,
    ) -> Summary:
        if not reviews:
            raise ValueError("Нет отзывов для суммаризации")

        parsed_params = AspectEvidenceGuidedParams.model_validate(params or {})
        normalizer = ReviewNormalizer()
        normalized_reviews = normalizer.normalize(reviews)
        if not normalized_reviews:
            raise ValueError("Нет нормализуемых текстов отзывов")

        segmenter = SpanSegmenter(max_spans_per_review=parsed_params.max_spans_per_review)
        spans = segmenter.segment(normalized_reviews)

        candidate_generator = AspectCandidateGenerator(
            min_candidate_len=parsed_params.min_candidate_len,
            max_candidates=parsed_params.max_candidates,
            enable_keybert_refinement=parsed_params.enable_keybert_refinement,
            embedding_model_name=parsed_params.embedding_model_name,
        )
        candidates = candidate_generator.generate(spans)

        mention_extractor = HeuristicMentionExtractor()
        mentions = mention_extractor.extract(spans, candidates)
        if not mentions:
            logger.warning("AspectEvidenceGuided: не удалось извлечь упоминания аспектов")
            return self._empty_summary(product_id=product_id, reviews=reviews, params=parsed_params)

        canonicalizer = AspectCanonicalizer(embedding_model_name=parsed_params.embedding_model_name)
        canonical_aspects = canonicalizer.canonicalize(mentions)

        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(canonical_aspects, reviews_count=len(reviews))

        scorer = AspectScorer()
        scored_aspects = scorer.score(aggregated, parsed_params)

        planner = ContentPlanner()
        plan = planner.build_plan(scored_aspects, parsed_params)

        evidence_selector = EvidenceSelector()
        evidence_items = evidence_selector.select(
            plan=plan,
            canonical_aspects=canonical_aspects,
            evidence_per_aspect=parsed_params.evidence_per_aspect,
        )

        if parsed_params.enable_llm_refinement and self._openai_client is not None:
            generation_input = self._build_generation_input(
                plan=plan,
                evidence_items=evidence_items,
                scored_aspects=scored_aspects,
                reviews=reviews,
                product_id=product_id,
                params=parsed_params,
            )
            try:
                llm_gen = LLMGroundedGenerator(self._openai_client)
                generated = await llm_gen.generate(generation_input)
            except Exception as exc:
                logger.warning(
                    "AspectEvidenceGuided: LLM generation failed, fallback на GroundedGenerator: {}",
                    exc,
                )
                generated = GroundedGenerator().generate(plan=plan, evidence_items=evidence_items)

            try:
                llm_ver = LLMSummaryVerifier(self._openai_client)
                verification = await llm_ver.verify(generation_input, generated)
            except Exception as exc:
                logger.warning(
                    "AspectEvidenceGuided: LLM verification failed, fallback на SummaryVerifier: {}",
                    exc,
                )
                verification = SummaryVerifier().verify(
                    plan=plan, evidence_items=evidence_items, output=generated
                )
        else:
            generated = GroundedGenerator().generate(plan=plan, evidence_items=evidence_items)
            verification = SummaryVerifier().verify(
                plan=plan, evidence_items=evidence_items, output=generated
            )

        final_output = verification.revised_output or generated

        if not verification.passed:
            logger.warning(
                "AspectEvidenceGuided verification failed: {}",
                "; ".join(verification.errors),
            )
            final_output = generated

        summary_id = uuid4()
        summary = self._build_summary(
            summary_id=summary_id,
            product_id=product_id,
            reviews=reviews,
            params=parsed_params,
            final_output=final_output,
            scored_aspects=scored_aspects,
            diagnostics={
                "verification_passed": verification.passed,
                "verification_errors": verification.errors,
                "verification_warnings": verification.warnings,
                "mentions_count": len(mentions),
                "candidates_count": len(candidates),
            },
        )

        await self._save_pending_artifacts(
            summary_id=summary_id,
            pending=PendingArtifacts(
                product_id=summary.product_id,
                mentions=mentions,
                scored_aspects=scored_aspects,
                plan=plan,
                evidence_items=evidence_items,
                extractor_version=mention_extractor.version,
            ),
        )
        return summary

    async def persist_artifacts(self, summary: Summary) -> None:
        if summary.id is None:
            logger.warning("Summary ID отсутствует, artifacts не будут сохранены")
            return

        async with self._pending_lock:
            pending = self._pending_artifacts.pop(summary.id, None)

        if pending is None:
            return

        await self._persist_artifacts(
            product_id=pending.product_id,
            summary_id=summary.id,
            mentions=pending.mentions,
            scored_aspects=pending.scored_aspects,
            plan=pending.plan,
            evidence_items=pending.evidence_items,
            extractor_version=pending.extractor_version,
        )

    async def _save_pending_artifacts(self, summary_id: UUID, pending: PendingArtifacts) -> None:
        async with self._pending_lock:
            self._pending_artifacts[summary_id] = pending

    def _build_summary(
        self,
        summary_id: UUID,
        product_id: str,
        reviews: list[Review],
        params: AspectEvidenceGuidedParams,
        final_output,
        scored_aspects: list[AspectStats],
        diagnostics: dict,
    ) -> Summary:
        ratings = [review.rating for review in reviews if review.rating is not None]
        dates = [review.review_date for review in reviews if review.review_date is not None]
        key_phrases = [
            KeyPhraseItem(
                phrase=aspect.aspect_name,
                sentiment="neutral",
                count=aspect.total_mentions,
                share=round(aspect.prevalence_score, 3),
            )
            for aspect in scored_aspects[:25]
        ]
        serialized_params = {
            **params.to_reproducible_params(),
            "method_version": self.version,
            "planner_version": self.PLANNER_VERSION,
            "pipeline_version": self.PIPELINE_VERSION,
            "diagnostics": diagnostics,
        }
        return Summary(
            id=summary_id,
            product_id=UUID(product_id) if isinstance(product_id, str) else product_id,
            method=self.code,
            method_version=self.version,
            params=serialized_params,
            created_at=datetime.now(),
            reviews_count=len(reviews),
            rating_avg=(sum(ratings) / len(ratings)) if ratings else None,
            date_min=min(dates) if dates else None,
            date_max=max(dates) if dates else None,
            text_overall=final_output.text_overall,
            text_neutral=final_output.text_neutral,
            text_pros=final_output.text_pros,
            text_cons=final_output.text_cons,
            key_phrases=key_phrases if key_phrases else None,
        )

    async def _persist_artifacts(
        self,
        product_id: UUID,
        summary_id: UUID,
        mentions,
        scored_aspects: list[AspectStats],
        plan,
        evidence_items,
        extractor_version: str,
    ) -> None:
        mention_rows = [
            AspectMentionDB(
                product_id=product_id,
                review_id=item.review_id,
                summary_id=summary_id,
                span_text=item.span_text,
                section_type=item.section_type.value,
                aspect_raw=item.aspect_raw,
                aspect_candidate=item.aspect_candidate,
                sentiment_label=item.sentiment_label.value,
                sentiment_score=item.sentiment_score,
                extractor_confidence=item.extractor_confidence,
                extractor_version=extractor_version,
            )
            for item in mentions
        ]
        await self._aspect_mention_repository.create_many(mention_rows)

        clusters = [
            AspectClusterDB(
                product_id=product_id,
                summary_id=summary_id,
                aspect_name=aspect.aspect_name,
                aliases_json={"aliases": aspect.aliases},
                total_mentions=aspect.total_mentions,
                positive_mentions=aspect.positive_mentions,
                negative_mentions=aspect.negative_mentions,
                neutral_mentions=aspect.neutral_mentions,
                mixed_mentions=aspect.mixed_mentions,
                importance_score=aspect.importance_score,
                prevalence_score=aspect.prevalence_score,
                polarity_balance_score=aspect.polarity_balance_score,
                rarity_flag=aspect.rarity_flag,
            )
            for aspect in scored_aspects
        ]
        await self._aspect_cluster_repository.create_many(clusters)
        cluster_id_by_aspect = {cluster.aspect_name: cluster.id for cluster in clusters}

        plan_row = SummaryPlanDB(
            summary_id=summary_id,
            selected_aspects_json={
                "items": [item.model_dump() for item in plan.selected_aspects],
            },
            dropped_aspects_json={"items": plan.dropped_aspects},
            diagnostics_json=plan.diagnostics,
            planner_version=self.PLANNER_VERSION,
        )
        await self._summary_plan_repository.create(plan_row)

        evidence_rows = []
        for evidence in evidence_items:
            cluster_id = cluster_id_by_aspect.get(evidence.aspect_name)
            if cluster_id is None:
                continue
            evidence_rows.append(
                SummaryEvidenceDB(
                    summary_id=summary_id,
                    aspect_cluster_id=cluster_id,
                    review_id=evidence.review_id,
                    evidence_text=evidence.evidence_text,
                    evidence_rank=evidence.rank,
                    used_in_final_summary=True,
                    supports_polarity=evidence.polarity.value,
                )
            )
        await self._summary_evidence_repository.create_many(evidence_rows)

    def _build_generation_input(
        self,
        plan: ContentPlan,
        evidence_items: list[EvidenceItem],
        scored_aspects: list[AspectStats],
        reviews: list[Review],
        product_id: str,
        params: AspectEvidenceGuidedParams,
    ) -> SummaryGenerationInput:
        """Собирает SummaryGenerationInput из результатов аналитического пайплайна."""
        stats_by_name: dict[str, AspectStats] = {s.aspect_name: s for s in scored_aspects}

        evidence_by_aspect: dict[str, list[EvidenceItem]] = defaultdict(list)
        for item in evidence_items:
            evidence_by_aspect[item.aspect_name].append(item)

        aspect_inputs: list[AspectSummaryInput] = []
        for planned in plan.selected_aspects:
            stats = stats_by_name.get(planned.aspect_name)
            ev_items = sorted(
                evidence_by_aspect.get(planned.aspect_name, []),
                key=lambda x: x.rank,
            )
            top_evidence = ev_items[: params.evidence_per_aspect]
            ev_count = max(1, len(ev_items))
            representative_evidence = [
                EvidenceInput(
                    text=ev.evidence_text,
                    section_type=ev.section_type,
                    sentiment_label=ev.polarity,
                    evidence_score=round(1.0 - (ev.rank - 1) / ev_count, 3),
                )
                for ev in top_evidence
            ]
            aspect_inputs.append(
                AspectSummaryInput(
                    aspect_name=planned.aspect_name,
                    importance_score=round(planned.importance_score, 3),
                    prevalence_score=round(stats.prevalence_score if stats else 0.0, 3),
                    total_mentions=stats.total_mentions if stats else 0,
                    positive_mentions=stats.positive_mentions if stats else 0,
                    negative_mentions=stats.negative_mentions if stats else 0,
                    neutral_mentions=stats.neutral_mentions if stats else 0,
                    target_polarity=planned.target_polarity,
                    rarity_flag=planned.rarity_flag,
                    must_include=planned.rarity_flag,
                    aliases=stats.aliases if stats else [],
                    representative_evidence=representative_evidence,
                )
            )

        ratings = [r.rating for r in reviews if r.rating is not None]
        rating_avg = sum(ratings) / len(ratings) if ratings else None

        return SummaryGenerationInput(
            product_id=UUID(product_id) if isinstance(product_id, str) else product_id,
            reviews_count=len(reviews),
            rating_avg=round(rating_avg, 2) if rating_avg is not None else None,
            selected_aspects=aspect_inputs,
            generation_constraints=GenerationConstraints(
                category=params.category,
                max_sentences=params.llm_overall_sentences,
            ),
        )

    def _empty_summary(
        self,
        product_id: str,
        reviews: list[Review],
        params: AspectEvidenceGuidedParams,
    ) -> Summary:
        ratings = [review.rating for review in reviews if review.rating is not None]
        dates = [review.review_date for review in reviews if review.review_date is not None]
        return Summary(
            product_id=UUID(product_id) if isinstance(product_id, str) else product_id,
            method=self.code,
            method_version=self.version,
            params=params.to_reproducible_params(),
            created_at=datetime.now(),
            reviews_count=len(reviews),
            rating_avg=(sum(ratings) / len(ratings)) if ratings else None,
            date_min=min(dates) if dates else None,
            date_max=max(dates) if dates else None,
            text_overall=None,
            text_neutral=None,
            text_pros=None,
            text_cons=None,
            key_phrases=None,
        )
