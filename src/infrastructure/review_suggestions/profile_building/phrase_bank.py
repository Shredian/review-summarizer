from __future__ import annotations

import re
from collections import Counter, defaultdict
from uuid import uuid4

from rapidfuzz import fuzz

from src.domain.review_suggestions.entities import (
    DiscoveredAspect,
    KeyphraseCandidate,
    PhraseCandidate,
    ReviewSegment,
)

_SPECIFIC = re.compile(
    r"\d+\s*(руб|₽|месяц|недел|дн|дней|час)|достав|заказ|купил",
    re.I,
)


def _dup_key(s: str) -> str:
    return " ".join(s.lower().split())


def dedupe_phrases(cands: list[PhraseCandidate], threshold: int = 92) -> list[PhraseCandidate]:
    kept: list[PhraseCandidate] = []
    for c in sorted(cands, key=lambda x: x.quality_score, reverse=True):
        ok = True
        for k in kept:
            if fuzz.ratio(_dup_key(c.text), _dup_key(k.text)) >= threshold:
                ok = False
                break
        if ok:
            kept.append(c)
    return kept


class ProductPhraseBankBuilder:
    def build(
        self,
        segments: list[ReviewSegment],
        aspects: list[DiscoveredAspect],
        keyphrases: list[KeyphraseCandidate],
    ) -> list[PhraseCandidate]:
        freq_surface: Counter[str] = Counter()
        rating_sum: dict[str, float] = defaultdict(float)
        rating_cnt: dict[str, int] = defaultdict(int)
        field_for: dict[str, str] = {}
        sent_for: dict[str, str] = {}

        for seg in segments:
            toks = seg.surface_tokens
            if len(toks) < 2:
                continue
            for n in (2, 3):
                for i in range(len(toks) - n + 1):
                    ph = " ".join(toks[i : i + n])
                    if len(ph) < 4:
                        continue
                    k = _dup_key(ph)
                    freq_surface[k] += 1
                    field_for[k] = seg.field
                    sent_for[k] = seg.weak_sentiment
                    if seg.rating is not None:
                        rating_sum[k] += seg.rating
                        rating_cnt[k] += 1

        phrases: list[PhraseCandidate] = []
        aspect_by_kw: dict[str, tuple[str, str]] = {}
        for asp in aspects:
            for kw in asp.keywords:
                aspect_by_kw[_dup_key(kw)] = (asp.aspect_id, asp.label)

        def add_phrase(
            text: str,
            *,
            weak_s: str,
            src_field: str,
            fq: int,
            avg_r: float | None,
            asp: tuple[str, str] | None,
            base_quality: float,
        ) -> None:
            if len(text) > 120:
                return
            if _SPECIFIC.search(text):
                return
            norm = _dup_key(text)
            aid, alab = asp if asp else (None, None)
            phrases.append(
                PhraseCandidate(
                    id=str(uuid4()),
                    text=text,
                    normalized_text=norm,
                    lemmas=norm.split(),
                    aspect_id=aid,
                    aspect_label=alab,
                    weak_sentiment=weak_s,
                    source_field=src_field,
                    frequency=fq,
                    avg_rating=avg_r,
                    length_tokens=len(norm.split()),
                    quality_score=base_quality,
                    contains_specific_fact=bool(_SPECIFIC.search(text)),
                )
            )

        for norm, fq in freq_surface.items():
            if fq < 2:
                continue
            text = norm
            avg_r = rating_sum[norm] / rating_cnt[norm] if rating_cnt[norm] else None
            asp = aspect_by_kw.get(norm)
            add_phrase(
                text,
                weak_s=sent_for.get(norm, "neutral"),
                src_field=field_for.get(norm, "comment"),
                fq=fq,
                avg_r=avg_r,
                asp=asp,
                base_quality=min(1.0, 0.3 + fq / 20.0),
            )

        for k in keyphrases[:120]:
            asp = aspect_by_kw.get(_dup_key(k.text))
            add_phrase(
                k.text,
                weak_s=k.weak_sentiment,
                src_field=k.field,
                fq=1,
                avg_r=None,
                asp=asp,
                base_quality=float(k.score),
            )

        for asp in aspects:
            for ph in asp.representative_phrases[:10]:
                add_phrase(
                    ph,
                    weak_s="neutral",
                    src_field="comment",
                    fq=1,
                    avg_r=None,
                    asp=(asp.aspect_id, asp.label),
                    base_quality=0.55,
                )

        return dedupe_phrases(phrases)
