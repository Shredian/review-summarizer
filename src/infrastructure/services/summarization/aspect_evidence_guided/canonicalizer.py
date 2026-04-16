from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
from typing import Iterable

from src.infrastructure.services.summarization.aspect_evidence_guided.embedding_cache import (
    get_shared_sentence_transformer,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    CanonicalAspect,
    MentionExtractionResult,
)

try:
    from sklearn.cluster import AgglomerativeClustering
except ImportError:  # pragma: no cover
    AgglomerativeClustering = None


class AspectCanonicalizer:
    """Объединяет candidate labels в канонические кластеры."""

    def __init__(self, embedding_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> None:
        self._embedder = get_shared_sentence_transformer(embedding_model_name)

    def canonicalize(self, mentions: Iterable[MentionExtractionResult]) -> list[CanonicalAspect]:
        mention_list = list(mentions)
        if not mention_list:
            return []

        labels = list({mention.aspect_candidate.strip().lower() for mention in mention_list if mention.aspect_candidate})
        if not labels:
            return []

        if self._embedder is not None and AgglomerativeClustering is not None and len(labels) > 2:
            clusters = self._cluster_with_embeddings(labels)
        else:
            clusters = self._cluster_with_similarity(labels)

        grouped_mentions: list[CanonicalAspect] = []
        for cluster_labels in clusters:
            canonical_name = min(cluster_labels, key=len)
            cluster_mentions = [
                mention
                for mention in mention_list
                if mention.aspect_candidate.strip().lower() in cluster_labels
            ]
            grouped_mentions.append(
                CanonicalAspect(
                    canonical_name=canonical_name,
                    aliases=sorted(cluster_labels),
                    mentions=cluster_mentions,
                )
            )
        return grouped_mentions

    def _cluster_with_embeddings(self, labels: list[str]) -> list[set[str]]:
        embeddings = self._embedder.encode(labels)
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1.1,
            metric="euclidean",
            linkage="average",
        )
        assignments = clustering.fit_predict(embeddings)
        grouped: dict[int, set[str]] = defaultdict(set)
        for index, cluster_id in enumerate(assignments):
            grouped[int(cluster_id)].add(labels[index])
        return list(grouped.values())

    def _cluster_with_similarity(self, labels: list[str]) -> list[set[str]]:
        clusters: list[set[str]] = []
        for label in labels:
            attached = False
            for cluster in clusters:
                if any(SequenceMatcher(None, label, other).ratio() >= 0.74 for other in cluster):
                    cluster.add(label)
                    attached = True
                    break
            if not attached:
                clusters.append({label})
        return clusters
