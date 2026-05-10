from __future__ import annotations

from typing import Any

from src.domain.review_suggestions.entities import PhraseCandidate


class ProductPrefixIndexBuilder:
    def build(
        self, phrase_bank: list[PhraseCandidate], cfg_min: int = 2, cfg_max: int = 40
    ) -> dict[str, Any]:
        idx: dict[str, list[dict[str, Any]]] = {}
        for p in phrase_bank:
            text = p.text.strip()
            if len(text) < cfg_min:
                continue
            inserts: set[str] = set()
            words = text.split()
            inserts.add(text)
            for w in words:
                if len(w) >= 3:
                    inserts.add(w)
            for ins in inserts:
                low = ins.lower()
                max_pos = min(cfg_max, len(low))
                for end in range(cfg_min, max_pos + 1):
                    prefix = low[:end]
                    bucket = idx.setdefault(prefix, [])
                    item = {
                        "text": text,
                        "insert_text": ins if ins in text else text,
                        "score": float(p.quality_score),
                        "aspect_id": p.aspect_id,
                        "weak_sentiment": p.weak_sentiment,
                    }
                    bucket.append(item)
        out: dict[str, list[dict[str, Any]]] = {}
        for pref, items in idx.items():
            items = sorted(items, key=lambda x: x["score"], reverse=True)[:20]
            out[pref] = items
        return out
