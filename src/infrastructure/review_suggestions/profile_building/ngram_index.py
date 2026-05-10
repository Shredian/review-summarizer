from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.domain.review_suggestions.entities import DiscoveredAspect, ReviewSegment


class ProductNgramIndexBuilder:
    def build(
        self,
        segments: list[ReviewSegment],
        aspects: list[DiscoveredAspect],
    ) -> dict[str, Any]:
        lemma_next: dict[str, list[dict[str, Any]]] = defaultdict(list)
        surface_next: dict[str, list[dict[str, Any]]] = defaultdict(list)
        asp_kw_map: dict[str, str] = {}
        for a in aspects:
            for k in a.keywords:
                kn = " ".join(k.lower().split())
                if kn:
                    asp_kw_map[kn] = a.aspect_id

        def find_aspect_id(bigram: str) -> str | None:
            low = bigram.lower()
            for kn, aid in asp_kw_map.items():
                if kn in low:
                    return aid
            return None

        def bump(
            store: dict[str, list[dict[str, Any]]],
            ctx: str,
            cont: str,
            sent: str,
        ) -> None:
            lst = store[ctx]
            for item in lst:
                if item["text"] == cont:
                    item["count"] += 1
                    item["score"] = min(1.0, 0.5 + item["count"] / 15.0)
                    return
            aid = find_aspect_id(f"{ctx} {cont}")
            lst.append(
                {
                    "text": cont,
                    "score": 0.55,
                    "count": 1,
                    "aspect_id": aid,
                    "weak_sentiment": sent,
                }
            )

        for seg in segments:
            surf = seg.surface_tokens
            lem = seg.lemmas
            if len(surf) < 2 or len(lem) < 2:
                continue
            for i in range(len(surf) - 1):
                for w in (1, 2, 3, 4):
                    if i - w + 1 < 0:
                        continue
                    ctx_s = " ".join(surf[i - w + 1 : i + 1])
                    if i + 1 >= len(surf):
                        continue
                    nxt_s = surf[i + 1]
                    bump(surface_next, ctx_s, nxt_s, seg.weak_sentiment)

            for i in range(len(lem) - 1):
                for w in (1, 2, 3, 4):
                    if i - w + 1 < 0:
                        continue
                    ctx_l = " ".join(lem[i - w + 1 : i + 1])
                    rest = lem[i + 1 : i + 3]
                    if not rest:
                        continue
                    cont = " ".join(rest)
                    bump(lemma_next, ctx_l, cont, seg.weak_sentiment)

        return {
            "lemma_contexts": {k: v[:30] for k, v in lemma_next.items()},
            "surface_contexts": {k: v[:30] for k, v in surface_next.items()},
        }
