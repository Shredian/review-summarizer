from __future__ import annotations

import re
from collections import Counter

import yake

from src.domain.review_suggestions.entities import (
    KeyphraseCandidate,
    KeyphraseSource,
    ReviewSegment,
)

_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
_PHONE = re.compile(r"(\+?\d[\d\s\-]{8,}\d)")
_TOO_MANY_DIGITS = re.compile(r"\d.*\d.*\d.*\d")

_RU_STOP = {
    "и",
    "в",
    "во",
    "на",
    "по",
    "к",
    "с",
    "у",
    "о",
    "об",
    "для",
    "не",
    "нет",
    "это",
    "как",
    "что",
    "все",
    "всё",
    "а",
    "но",
}


def _passes_filters(phrase: str) -> bool:
    p = phrase.strip()
    if not p or len(p) > 120:
        return False
    if _EMAIL.search(p) or _PHONE.search(p):
        return False
    toks = p.split()
    if len(toks) < 1 or len(toks) > 5:
        return False
    if _TOO_MANY_DIGITS.search(p):
        return False
    if all(t.lower() in _RU_STOP for t in toks if t.isalpha()):
        return False
    # эвристика «конкретный опыт»
    low = p.lower()
    return not any(
        x in low
        for x in (
            "месяц",
            "неделю",
            "дней",
            "дня",
            "часов",
            "руб",
            "₽",
            "купил",
            "заказал",
            "достав",
        )
    )


def _ngram_phrases(
    segments: list[ReviewSegment],
    max_n: int = 3,
    min_freq: int = 2,
) -> list[tuple[str, float, ReviewSegment]]:
    counts: Counter[tuple[str, ...]] = Counter()
    lemma_to_example: dict[tuple[str, ...], ReviewSegment] = {}
    for seg in segments:
        lem = seg.lemmas
        if len(lem) < 1:
            continue
        for n in range(1, min(max_n, len(lem)) + 1):
            for i in range(len(lem) - n + 1):
                ng = tuple(lem[i : i + n])
                if any(not x or x in _RU_STOP for x in ng):
                    continue
                counts[ng] += 1
                lemma_to_example.setdefault(ng, seg)
    out: list[tuple[str, float, ReviewSegment]] = []
    for ng, c in counts.items():
        if c < min_freq:
            continue
        text = " ".join(ng)
        if not _passes_filters(text):
            continue
        score = min(1.0, c / 10.0)
        out.append((text, score, lemma_to_example[ng]))
    return out


def _yake_phrases(
    segments: list[ReviewSegment], top: int = 80
) -> list[tuple[str, float, ReviewSegment]]:
    full = "\n".join(s.raw_text for s in segments[:2000])
    if len(full.strip()) < 10:
        return []
    kw = yake.KeywordExtractor(lan="ru", n=3, dedupLim=0.9, top=top, features=None)
    pairs = kw.extract_keywords(full)
    out: list[tuple[str, float, ReviewSegment]] = []
    for phrase, score in pairs:
        if not _passes_filters(phrase):
            continue
        # yake: lower score is better — инвертируем
        sc = max(0.0, min(1.0, 1.0 - float(score)))
        out.append((phrase.strip(), sc, segments[0]))
    return out


def _try_keybert(
    segments: list[ReviewSegment],
    model_name: str,
) -> list[tuple[str, float, ReviewSegment]]:
    try:
        from keybert import KeyBERT
        from sentence_transformers import SentenceTransformer
    except ImportError:  # pragma: no cover
        return []
    docs = [s.raw_text for s in segments if len(s.raw_text) >= 8]
    if not docs:
        return []
    st = SentenceTransformer(model_name)
    kw = KeyBERT(model=st)
    out: list[tuple[str, float, ReviewSegment]] = []
    # батч по одному документу для простоты
    for seg in segments[:200]:
        kws = kw.extract_keywords(seg.raw_text, keyphrase_ngram_range=(1, 3), top_n=3)
        for ph, sc in kws:
            if not _passes_filters(ph):
                continue
            out.append((ph.strip(), float(sc), seg))
    return out


class KeyphraseExtractor:
    def __init__(self, embedding_model: str) -> None:
        self._embedding_model = embedding_model

    def extract(self, segments: list[ReviewSegment]) -> list[KeyphraseCandidate]:
        cands: list[KeyphraseCandidate] = []
        seen: set[str] = set()

        def add(
            text: str,
            score: float,
            source: KeyphraseSource,
            seg: ReviewSegment,
        ) -> None:
            norm = " ".join(text.lower().split())
            if norm in seen:
                return
            seen.add(norm)
            lemmas = seg.lemmas[:5]
            cands.append(
                KeyphraseCandidate(
                    text=text,
                    normalized_text=norm,
                    lemmas=lemmas,
                    source=source,
                    segment_id=seg.segment_id,
                    field=seg.field,
                    weak_sentiment=seg.weak_sentiment,
                    score=score,
                )
            )

        for text, sc, seg in _yake_phrases(segments):
            add(text, sc, "yake", seg)
        for text, sc, seg in _ngram_phrases(segments):
            add(text, sc, "ngram", seg)
        for text, sc, seg in _try_keybert(segments, self._embedding_model):
            add(text, sc, "keybert", seg)

        cands.sort(key=lambda x: x.score, reverse=True)
        return cands[:400]
