from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from src.domain.review_suggestions.entities import (
    DiscoveredAspect,
    KeyphraseCandidate,
    ReviewSegment,
)


def _embed_texts(texts: list[str], model_name: str) -> np.ndarray | None:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:  # pragma: no cover
        return None
    if not texts:
        return None
    model = SentenceTransformer(model_name)
    return np.asarray(model.encode(texts, show_progress_bar=False))


@dataclass
class AspectDiscoveryConfig:
    reviews_count: int
    segments_count: int
    embedding_model: str


class ProductAspectDiscoveryService:
    def discover(
        self,
        segments: list[ReviewSegment],
        keyphrases: list[KeyphraseCandidate],
        cfg: AspectDiscoveryConfig,
    ) -> list[DiscoveredAspect]:
        small = cfg.reviews_count < 5 or cfg.segments_count < 20
        texts = [k.normalized_text for k in keyphrases[:300]]
        if not texts and segments:
            texts = [s.normalized_text for s in segments[:200]]
        if not texts:
            return []
        emb = _embed_texts(texts, cfg.embedding_model)
        if emb is None:
            return self._pseudo_aspects_from_keyphrases(keyphrases[:40])

        if not small:
            aspects = self._try_bertopic(texts, emb, keyphrases, segments)
            if aspects:
                return aspects
        return self._cluster_embeddings_fallback(texts, emb, keyphrases, segments)

    def _try_bertopic(
        self,
        texts: list[str],
        emb: np.ndarray,
        keyphrases: list[KeyphraseCandidate],
        segments: list[ReviewSegment],
    ) -> list[DiscoveredAspect]:
        try:
            from bertopic import BERTopic
            from hdbscan import HDBSCAN
            from umap import UMAP
        except ImportError:  # pragma: no cover
            return []
        if len(texts) < 10:
            return []
        try:
            topic_model = BERTopic(
                embedding_model=None,
                umap_model=UMAP(n_neighbors=10, n_components=5, metric="cosine", random_state=42),
                hdbscan_model=HDBSCAN(min_cluster_size=3, metric="euclidean", prediction_data=True),
                verbose=False,
                calculate_probabilities=True,
            )
            topics, probs = topic_model.fit_transform(texts, embeddings=emb)
        except Exception:
            return []
        aspects: list[DiscoveredAspect] = []
        topic_ids = sorted(set(topics))
        for tid in topic_ids:
            if tid == -1:
                continue
            idxs = [i for i, t in enumerate(topics) if t == tid]
            kw_subset = [keyphrases[i] for i in idxs if i < len(keyphrases)]
            label = kw_subset[0].text if kw_subset else texts[idxs[0]]
            aspects.append(
                DiscoveredAspect(
                    aspect_id=f"aspect_{tid}",
                    label=label[:80],
                    keywords=[k.text for k in kw_subset[:12]],
                    representative_phrases=[k.text for k in kw_subset[:8]],
                    positive_phrases=[k.text for k in kw_subset if k.weak_sentiment == "positive"][
                        :8
                    ],
                    negative_phrases=[k.text for k in kw_subset if k.weak_sentiment == "negative"][
                        :8
                    ],
                    neutral_phrases=[
                        k.text
                        for k in kw_subset
                        if k.weak_sentiment not in ("positive", "negative")
                    ][:8],
                    segment_count=len(idxs),
                    confidence=float(np.mean(probs[idxs]))
                    if probs is not None and len(probs)
                    else 0.5,
                )
            )
        if aspects:
            return aspects
        return self._cluster_embeddings_fallback(texts, emb, keyphrases, segments)

    def _cluster_embeddings_fallback(
        self,
        texts: list[str],
        emb: np.ndarray,
        keyphrases: list[KeyphraseCandidate],
        segments: list[ReviewSegment],
    ) -> list[DiscoveredAspect]:
        from sklearn.cluster import AgglomerativeClustering

        n = len(texts)
        if n < 2:
            return self._pseudo_aspects_from_keyphrases(keyphrases)
        cl = AgglomerativeClustering(
            n_clusters=None, distance_threshold=1.0, metric="cosine", linkage="average"
        )
        labels = cl.fit_predict(emb)
        aspects: list[DiscoveredAspect] = []
        for tid in sorted(set(labels)):
            idxs = [i for i, t in enumerate(labels) if t == tid]
            kw_subset = [keyphrases[i] for i in idxs if i < len(keyphrases)]
            rep = [texts[i] for i in idxs[:5]]
            label = (kw_subset[0].text if kw_subset else rep[0])[:80]
            aspects.append(
                DiscoveredAspect(
                    aspect_id=f"aspect_{int(tid)}",
                    label=label,
                    keywords=rep[:12],
                    representative_phrases=rep[:8],
                    positive_phrases=[k.text for k in kw_subset if k.weak_sentiment == "positive"][
                        :8
                    ],
                    negative_phrases=[k.text for k in kw_subset if k.weak_sentiment == "negative"][
                        :8
                    ],
                    neutral_phrases=[
                        k.text
                        for k in kw_subset
                        if k.weak_sentiment not in ("positive", "negative")
                    ][:8],
                    segment_count=len(idxs),
                    confidence=0.45,
                )
            )
        return aspects or self._pseudo_aspects_from_keyphrases(keyphrases)

    def _pseudo_aspects_from_keyphrases(
        self,
        keyphrases: Sequence[KeyphraseCandidate],
    ) -> list[DiscoveredAspect]:
        aspects: list[DiscoveredAspect] = []
        for i, k in enumerate(keyphrases[:15]):
            aspects.append(
                DiscoveredAspect(
                    aspect_id=f"aspect_{i}",
                    label=k.text[:80],
                    keywords=[k.text],
                    representative_phrases=[k.text],
                    positive_phrases=[k.text] if k.weak_sentiment == "positive" else [],
                    negative_phrases=[k.text] if k.weak_sentiment == "negative" else [],
                    neutral_phrases=[k.text]
                    if k.weak_sentiment not in ("positive", "negative")
                    else [],
                    segment_count=1,
                    confidence=float(k.score),
                )
            )
        return aspects
