from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Iterable
from uuid import UUID, uuid4

from src.domain.models.review import Review
from src.domain.evaluation.config import EvaluationRunConfig
from src.infrastructure.db.models.benchmark_product import BenchmarkProductDB
from src.infrastructure.db.models.benchmark_review import BenchmarkReviewDB
from src.infrastructure.db.models.reference_aspect import ReferenceAspectDB
from src.infrastructure.db.models.reference_evidence import ReferenceEvidenceDB
from src.infrastructure.db.models.reference_ledger import ReferenceLedgerDB
from src.infrastructure.services.summarization.aspect_evidence_guided.aspect_candidates import (
    AspectCandidateGenerator,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.canonicalizer import (
    AspectCanonicalizer,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.mention_extractor import (
    HeuristicMentionExtractor,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.normalizer import (
    ReviewNormalizer,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    SentimentLabel,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.segmenter import (
    SpanSegmenter,
)

from src.utils.logger import logger


def benchmark_reviews_to_domain(
    product: BenchmarkProductDB,
    reviews: Iterable[BenchmarkReviewDB],
) -> list[Review]:
    """Маппинг benchmark отзывов в доменную модель (product_id = benchmark_product.id)."""
    out: list[Review] = []
    for br in reviews:
        out.append(
            Review(
                id=br.id,
                product_id=product.id,
                user_id=None,
                source=product.platform_name,
                url=br.source_url,
                rating=br.rating,
                title=br.title,
                comment=br.comment,
                plus=br.plus,
                minus=br.minus,
                review_date=br.review_date,
                created_at=datetime.now(UTC),
            )
        )
    return out


def _dominant_polarity(labels: Counter) -> str:
    if not labels:
        return SentimentLabel.NEUTRAL.value
    m = {k: float(labels.get(k, 0)) for k in ("positive", "negative", "neutral", "mixed")}
    best = max(m.values())
    if best <= 0:
        return SentimentLabel.NEUTRAL.value
    leaders = [k for k, v in m.items() if v == best]
    if len(leaders) != 1:
        return "mixed"
    return leaders[0]


def build_reference_ledger_from_benchmark(
    product: BenchmarkProductDB,
    reviews: list[BenchmarkReviewDB],
    *,
    reference_version: str = "ledger_v1_draft",
    config: EvaluationRunConfig | None = None,
    max_evidences_per_aspect: int = 5,
) -> tuple[ReferenceLedgerDB, list[ReferenceAspectDB], list[list[ReferenceEvidenceDB]]]:
    """Строит draft reference ledger из отзывов (reuse AEG extraction + canonicalization)."""
    cfg = config or EvaluationRunConfig(benchmark_set_name=product.benchmark_set_name)
    domain_reviews = benchmark_reviews_to_domain(product, reviews)
    normalizer = ReviewNormalizer()
    normalized = normalizer.normalize(domain_reviews)
    segmenter = SpanSegmenter()
    spans = segmenter.segment(normalized)
    gen = AspectCandidateGenerator(embedding_model_name=cfg.embedding_model_name)
    candidates = gen.generate(spans)
    extractor = HeuristicMentionExtractor()
    mentions = extractor.extract(spans, candidates)
    canonicalizer = AspectCanonicalizer(embedding_model_name=cfg.embedding_model_name)
    aspects = canonicalizer.canonicalize(mentions)

    total_mentions = sum(len(a.mentions) for a in aspects) or 1
    ledger_id = uuid4()
    ledger = ReferenceLedgerDB(
        id=ledger_id,
        benchmark_product_id=product.id,
        reference_version=reference_version,
        created_at=datetime.now(UTC),
    )

    aspect_rows: list[ReferenceAspectDB] = []
    evidence_rows: list[list[ReferenceEvidenceDB]] = []

    for ca in aspects:
        aid = uuid4()
        labels = Counter(m.sentiment_label.value for m in ca.mentions)
        dist = {k: v / len(ca.mentions) for k, v in labels.items()}
        expected = _dominant_polarity(labels)
        salience = len(ca.mentions) / total_mentions
        review_ids = {m.review_id for m in ca.mentions}
        rare = len(ca.mentions) <= 2 and len(review_ids) <= 2 and len(ca.mentions) > 0

        aspect_rows.append(
            ReferenceAspectDB(
                id=aid,
                ledger_id=ledger_id,
                aspect_name=ca.canonical_name,
                salience_weight=float(salience),
                expected_polarity=expected,
                polarity_distribution_json=dist,
                rare_but_important=rare,
                aliases_json=list(ca.aliases),
            )
        )
        evs: list[ReferenceEvidenceDB] = []
        seen_text: set[str] = set()
        for m in ca.mentions:
            if len(evs) >= max_evidences_per_aspect:
                break
            key = (str(m.review_id), m.span_text.strip().lower())
            if key in seen_text:
                continue
            seen_text.add(key)
            evs.append(
                ReferenceEvidenceDB(
                    id=uuid4(),
                    reference_aspect_id=aid,
                    review_id=m.review_id,
                    text=m.span_text,
                    section_type=m.section_type.value,
                    polarity=m.sentiment_label.value,
                    evidence_strength=m.extractor_confidence,
                )
            )
        evidence_rows.append(evs)

    logger.info(
        "Reference ledger draft: product={} aspects={} mentions_total={}",
        product.id,
        len(aspect_rows),
        total_mentions,
    )
    return ledger, aspect_rows, evidence_rows
