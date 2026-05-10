from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID

from src.domain.models.review import Review
from src.domain.review_suggestions.source_hash import compute_product_source_hash
from src.infrastructure.review_suggestions.profile_building.aspects import (
    AspectDiscoveryConfig,
    ProductAspectDiscoveryService,
)
from src.infrastructure.review_suggestions.profile_building.keyphrases import KeyphraseExtractor
from src.infrastructure.review_suggestions.profile_building.ngram_index import (
    ProductNgramIndexBuilder,
)
from src.infrastructure.review_suggestions.profile_building.phrase_bank import (
    ProductPhraseBankBuilder,
)
from src.infrastructure.review_suggestions.profile_building.prefix_index import (
    ProductPrefixIndexBuilder,
)
from src.infrastructure.review_suggestions.profile_building.preprocessing import (
    ReviewTextPreprocessor,
)
from src.infrastructure.review_suggestions.profile_building.review_texts import (
    collect_review_texts_from_reviews,
)


def build_product_profile_payload(
    product_id: UUID,
    reviews: list[Review],
    *,
    embedding_model: str,
    pipeline_version: int,
) -> dict:
    texts = collect_review_texts_from_reviews(reviews)
    pre = ReviewTextPreprocessor()
    segments = pre.preprocess(texts)
    kx = KeyphraseExtractor(embedding_model)
    keyphrases = kx.extract(segments)
    disc = ProductAspectDiscoveryService()
    aspects = disc.discover(
        segments,
        keyphrases,
        AspectDiscoveryConfig(
            reviews_count=len({r.id for r in reviews if r.id}),
            segments_count=len(segments),
            embedding_model=embedding_model,
        ),
    )
    phrase_builder = ProductPhraseBankBuilder()
    phrases = phrase_builder.build(segments, aspects, keyphrases)
    ngram_builder = ProductNgramIndexBuilder()
    ngram_index = ngram_builder.build(segments, aspects)
    prefix_builder = ProductPrefixIndexBuilder()
    prefix_index = prefix_builder.build(phrases)
    sh = compute_product_source_hash(product_id, reviews)
    generic = [
        "в целом",
        "по ощущениям",
        "для ежедневного использования",
        "есть небольшие нюансы",
        "за свою цену",
    ]
    phrase_bank_ser = [asdict(p) for p in phrases[:2000]]
    aspects_ser = [asdict(a) for a in aspects]
    return {
        "product_id": str(product_id),
        "source_hash": sh,
        "phrase_bank": phrase_bank_ser,
        "aspects": aspects_ser,
        "ngram_index": ngram_index,
        "prefix_index": prefix_index,
        "generic_starters": generic,
        "metadata": {
            "reviews_count": len(reviews),
            "segments_count": len(segments),
            "built_at": datetime.now(UTC).isoformat(),
            "model_name": embedding_model,
            "pipeline_version": pipeline_version,
        },
    }


def build_user_profile_payload(
    user_id: UUID,
    reviews: list[Review],
    *,
    embedding_model: str,
    pipeline_version: int,
) -> dict:
    texts = collect_review_texts_from_reviews(reviews)
    pre = ReviewTextPreprocessor()
    segments = pre.preprocess(texts)
    kx = KeyphraseExtractor(embedding_model)
    keyphrases = kx.extract(segments)
    common = [k.normalized_text for k in keyphrases[:40]]
    openers = Counter()
    connectors = Counter()
    excl = 0
    lens: list[int] = []
    sent_lens: list[int] = []
    for seg in segments:
        lens.append(len(seg.surface_tokens))
        sent_lens.append(len(seg.surface_tokens))
        if "!" in seg.raw_text:
            excl += 1
        toks = seg.surface_tokens
        if toks:
            openers[toks[0]] += 1
        if len(toks) > 2:
            connectors[" ".join(toks[1:3])] += 1
    avg_review_len = sum(lens) / len(lens) if lens else 0.0
    avg_sent_len = sum(sent_lens) / len(sent_lens) if sent_lens else 0.0
    return {
        "user_id": str(user_id),
        "common_phrases": common,
        "common_openers": [w for w, _ in openers.most_common(15)],
        "common_connectors": [w for w, _ in connectors.most_common(15)],
        "avg_review_len_tokens": avg_review_len,
        "avg_sentence_len_tokens": avg_sent_len,
        "punctuation_profile": {"exclamation_rate": excl / max(1, len(segments))},
        "style_flags": {
            "short_practical": 1.0 if avg_sent_len < 8 else 0.3,
            "formal": 0.3,
            "emotional": min(1.0, excl / max(1, len(segments))),
        },
        "metadata": {
            "reviews_count": len(reviews),
            "built_at": datetime.now(UTC).isoformat(),
            "pipeline_version": pipeline_version,
            "model_name": embedding_model,
        },
    }
