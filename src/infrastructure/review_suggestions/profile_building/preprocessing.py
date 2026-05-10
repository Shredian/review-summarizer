from __future__ import annotations

import re
from typing import cast
from uuid import uuid4

import razdel
from pymorphy3 import MorphAnalyzer

from src.domain.review_suggestions.entities import ReviewSegment, ReviewText, WeakSentiment
from src.infrastructure.review_suggestions.profile_building.review_texts import (
    weak_sentiment_for_field,
)

_HTML_TAG = re.compile(r"<[^>]+>")
_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_MULTI_SPACE = re.compile(r"\s+")

_morph: MorphAnalyzer | None = None


def _get_morph() -> MorphAnalyzer:
    global _morph
    if _morph is None:
        _morph = MorphAnalyzer()
    return _morph


def _clean_text(s: str) -> str:
    s = _HTML_TAG.sub(" ", s)
    s = _URL.sub(" ", s)
    s = _MULTI_SPACE.sub(" ", s).strip()
    return s


def _count_informative_lemmas(lemmas: list[str]) -> int:
    morph = _get_morph()
    stop = {
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
        "да",
        "но",
        "а",
        "как",
        "что",
        "это",
        "все",
        "всё",
        "очень",
        "так",
        "уже",
    }
    n = 0
    for lem in lemmas:
        if not lem or lem in stop:
            continue
        p = morph.parse(lem)[0]
        # pymorphy3: `grammeme in tag` валидирует имя; «NUM» не является допустимой граммемой.
        # Ориентируемся на строковое представление OpenCorpora (PNCT, NUMR и т.д.).
        tag_u = str(p.tag).upper()
        if "PNCT" in tag_u or "NUMR" in tag_u:
            continue
        n += 1
    return n


class ReviewTextPreprocessor:
    """Разбиение текстов отзывов на сегменты с токенами и леммами."""

    def preprocess(self, texts: list[ReviewText]) -> list[ReviewSegment]:
        segments: list[ReviewSegment] = []
        for rt in texts:
            base = _clean_text(rt.text)
            if len(base) < 2:
                continue
            ws = weak_sentiment_for_field(rt.field, rt.rating)
            weak = cast(
                WeakSentiment,
                ws if ws in ("positive", "negative", "neutral", "mixed") else "neutral",
            )
            for sent in razdel.sentenize(base):
                st = str(sent).strip()
                if len(st) < 2:
                    continue
                surface_tokens = []
                for t in razdel.tokenize(st):
                    tx = t.text.lower()
                    if tx.isalnum() or tx.replace("-", "").isalnum():
                        surface_tokens.append(tx)
                if not surface_tokens:
                    continue
                morph = _get_morph()
                lemmas: list[str] = []
                for tok in surface_tokens:
                    p = morph.parse(tok)[0]
                    lemmas.append(p.normal_form.lower())
                norm = " ".join(surface_tokens)
                if len(norm) < 3:
                    continue
                _count_informative_lemmas(lemmas)  # reserved for future filtering
                seg_id = f"{rt.review_id}:{uuid4().hex[:12]}"
                segments.append(
                    ReviewSegment(
                        segment_id=seg_id,
                        review_id=rt.review_id,
                        product_id=rt.product_id,
                        user_id=rt.user_id,
                        field=rt.field,
                        raw_text=st,
                        normalized_text=norm,
                        surface_tokens=surface_tokens,
                        lemmas=lemmas,
                        rating=rt.rating,
                        weak_sentiment=weak,
                    )
                )
        return segments
