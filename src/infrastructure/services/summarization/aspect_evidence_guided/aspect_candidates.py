from __future__ import annotations

from collections import Counter
import re
from typing import Any, Iterable

from src.infrastructure.services.summarization.aspect_evidence_guided.embedding_cache import (
    get_shared_sentence_transformer,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import ReviewSpan

try:
    import spacy
except ImportError:  # pragma: no cover
    spacy = None

try:
    from keybert import KeyBERT
except ImportError:  # pragma: no cover
    KeyBERT = None

# Последовательности токенов с этими POS дают осмысленные номинальные группы (в т.ч. для русского).
_NOMINAL_POS = frozenset({"NOUN", "PROPN", "ADJ", "NUM"})


def nominal_spans_from_pos_pairs(
    token_pairs: list[tuple[str, str]],
    min_candidate_len: int,
) -> list[str]:
    """Строит строки-кандидаты из последовательностей подряд идущих NOUN/PROPN/ADJ/NUM.

    token_pairs: список (текст в lower, UD pos_).
    """
    results: list[str] = []
    current: list[str] = []
    for text, pos in token_pairs:
        if pos in _NOMINAL_POS:
            current.append(text)
        else:
            if current:
                candidate = " ".join(current).strip()
                if len(candidate) >= min_candidate_len:
                    results.append(candidate)
                current = []
    if current:
        candidate = " ".join(current).strip()
        if len(candidate) >= min_candidate_len:
            results.append(candidate)
    return results


def nominal_spans_from_spacy_doc(doc: Any, min_candidate_len: int) -> list[str]:
    pairs = [(token.text.lower(), token.pos_) for token in doc]
    return nominal_spans_from_pos_pairs(pairs, min_candidate_len)


class AspectCandidateGenerator:
    """Hybrid генератор аспект-кандидатов."""

    def __init__(
        self,
        min_candidate_len: int = 3,
        max_candidates: int = 120,
        enable_keybert_refinement: bool = False,
        embedding_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    ) -> None:
        self._min_candidate_len = min_candidate_len
        self._max_candidates = max_candidates
        self._enable_keybert_refinement = enable_keybert_refinement
        self._embedding_model_name = embedding_model_name
        self._nlp = self._build_nlp()
        self._keybert: Any = None
        if enable_keybert_refinement and KeyBERT is not None:
            embedder = get_shared_sentence_transformer(embedding_model_name)
            if embedder is not None:
                self._keybert = KeyBERT(model=embedder)

    def _build_nlp(self):  # type: ignore[no-untyped-def]
        if spacy is None:
            return None
        try:
            return spacy.load("ru_core_news_sm")
        except Exception:
            nlp = spacy.blank("ru")
            nlp.add_pipe("sentencizer")
            return nlp

    def generate(self, spans: Iterable[ReviewSpan]) -> list[str]:
        ngram_candidates = self._extract_ngrams(spans)
        noun_chunk_candidates = self._extract_noun_chunks(spans)
        keyword_candidates = self._extract_keywords(spans)

        merged = Counter(ngram_candidates + noun_chunk_candidates + keyword_candidates)
        candidates = [item for item, _ in merged.most_common(self._max_candidates)]
        return [candidate for candidate in candidates if len(candidate) >= self._min_candidate_len]

    def _extract_ngrams(self, spans: Iterable[ReviewSpan]) -> list[str]:
        results: list[str] = []
        for span in spans:
            tokens = re.findall(r"\w+", span.normalized_text)
            for n in (1, 2, 3):
                for idx in range(len(tokens) - n + 1):
                    candidate = " ".join(tokens[idx : idx + n]).strip()
                    if len(candidate) >= self._min_candidate_len:
                        results.append(candidate)
        return results

    def _extract_noun_chunks(self, spans: Iterable[ReviewSpan]) -> list[str]:
        if self._nlp is None:
            return []

        candidates: list[str] = []
        for span in spans:
            doc = self._nlp(span.span_text)
            try:
                for chunk in doc.noun_chunks:
                    text = chunk.text.strip().lower()
                    if len(text) >= self._min_candidate_len:
                        candidates.append(text)
            except (ValueError, NotImplementedError):
                # Без parser noun_chunks недоступны: номинальные группы по POS (лучше, чем слепые n-граммы).
                candidates.extend(nominal_spans_from_spacy_doc(doc, self._min_candidate_len))
        return candidates

    def _extract_keywords(self, spans: Iterable[ReviewSpan]) -> list[str]:
        span_texts = [span.span_text for span in spans]
        if not span_texts:
            return []

        if self._keybert is not None:
            joined = "\n".join(span_texts)
            extracted = self._keybert.extract_keywords(
                joined,
                keyphrase_ngram_range=(1, 3),
                stop_words=None,
                top_n=min(50, self._max_candidates),
            )
            return [item[0].strip().lower() for item in extracted if item and item[0]]

        # fallback keyword extraction without ML
        all_tokens: list[str] = []
        for text in span_texts:
            all_tokens.extend(re.findall(r"\w+", text.lower()))
        return [token for token, _ in Counter(all_tokens).most_common(50)]
