from __future__ import annotations

import uuid
from typing import Any

from rapidfuzz import fuzz

from src.domain.review_suggestions.entities import SuggestionCandidate, TextInputState


def _suggestion(
    text: str,
    insert_text: str,
    *,
    stype: str,
    insert_mode: str,
    source: str,
    aspect_id: str | None = None,
    aspect_label: str | None = None,
    prefix_score: float = 0.0,
    ngram_score: float = 0.0,
    aspect_score: float = 0.0,
    sentiment_score: float = 0.0,
    product_frequency_score: float = 0.0,
    user_style_score: float = 0.0,
    quality_score: float = 0.5,
    metadata: dict[str, Any] | None = None,
) -> SuggestionCandidate:
    return SuggestionCandidate(
        id=f"s_{uuid.uuid4().hex[:10]}",
        text=text,
        insert_text=insert_text,
        type=stype,
        insert_mode=insert_mode,
        aspect_id=aspect_id,
        aspect_label=aspect_label,
        confidence=0.5,
        source=source,
        prefix_score=prefix_score,
        ngram_score=ngram_score,
        aspect_score=aspect_score,
        sentiment_score=sentiment_score,
        product_frequency_score=product_frequency_score,
        user_style_score=user_style_score,
        quality_score=quality_score,
        metadata=metadata or {},
    )


class PrefixCandidateGenerator:
    def generate(self, state: TextInputState, profile: dict[str, Any]) -> list[SuggestionCandidate]:
        if not state.current_token or len(state.current_token) < 1:
            return []
        prefix_index: dict[str, list[dict[str, Any]]] = profile.get("prefix_index") or {}
        key = state.current_token[:40].lower()
        out: list[SuggestionCandidate] = []
        # перебор префиксов с укорочением
        for ln in range(len(key), 1, -1):
            sub = key[:ln]
            bucket = prefix_index.get(sub)
            if not bucket:
                continue
            for item in bucket[:15]:
                ins = str(item.get("insert_text") or item.get("text") or "")
                full = str(item.get("text") or "")
                ct = (state.current_token or "").lower()
                mode = "append"
                repl = ins
                if ct:
                    if full.lower().startswith(ct):
                        mode = "replace_current_token"
                        repl = full
                    elif ins.lower().startswith(ct):
                        # фраза из банка начинается с другого слова, а завершение — от insert_text («хор» → «хороший»)
                        mode = "replace_current_token"
                        repl = ins
                out.append(
                    _suggestion(
                        full,
                        repl,
                        stype="phrase_completion",
                        insert_mode=mode,
                        source="prefix",
                        aspect_id=item.get("aspect_id"),
                        prefix_score=float(item.get("score") or 0.6),
                        product_frequency_score=float(item.get("score") or 0.5),
                        metadata={"weak_sentiment": item.get("weak_sentiment")},
                    )
                )
            break
        return out


class NgramCandidateGenerator:
    def generate(self, state: TextInputState, profile: dict[str, Any]) -> list[SuggestionCandidate]:
        ng = profile.get("ngram_index") or {}
        lemma_ctx: dict[str, list[dict[str, Any]]] = ng.get("lemma_contexts") or {}
        surf_ctx: dict[str, list[dict[str, Any]]] = ng.get("surface_contexts") or {}
        tokens = state.last_surface_tokens or state.last_lemmas
        out: list[SuggestionCandidate] = []
        for ctx_len in (4, 3, 2, 1):
            if len(tokens) < ctx_len:
                continue
            ctx = " ".join(tokens[-ctx_len:])
            for store in (surf_ctx, lemma_ctx):
                conts = store.get(ctx)
                if not conts:
                    continue
                for item in conts[:12]:
                    out.append(
                        _suggestion(
                            str(item.get("text") or ""),
                            str(item.get("text") or ""),
                            stype="next_word",
                            insert_mode="append",
                            source="ngram",
                            aspect_id=item.get("aspect_id"),
                            ngram_score=float(item.get("score") or 0.55),
                            product_frequency_score=float(item.get("count") or 1) / 20.0,
                            sentiment_score=0.5,
                            metadata={"weak_sentiment": item.get("weak_sentiment")},
                        )
                    )
                if out:
                    return out
        return out


class DynamicAspectCandidateGenerator:
    def generate(self, state: TextInputState, profile: dict[str, Any]) -> list[SuggestionCandidate]:
        aspects: list[dict[str, Any]] = profile.get("aspects") or []
        out: list[SuggestionCandidate] = []
        ctx = " ".join(state.last_surface_tokens[-6:])
        for asp in aspects:
            label = str(asp.get("label") or "")
            aid = str(asp.get("aspect_id") or "")
            best = 0
            for kw in (asp.get("keywords") or [])[:20]:
                sc = fuzz.partial_ratio(ctx.lower(), str(kw).lower())
                best = max(best, sc)
            for ph in (asp.get("representative_phrases") or [])[:5]:
                sc = fuzz.partial_ratio(ctx.lower(), str(ph).lower())
                best = max(best, sc)
            if best >= 72:
                phrases = list(asp.get("representative_phrases") or [])[:3]
                sent = state.field
                pool = phrases
                if sent == "plus":
                    pool = (asp.get("positive_phrases") or phrases)[:3]
                elif sent == "minus":
                    pool = (asp.get("negative_phrases") or phrases)[:3]
                for ph in pool:
                    if not ph:
                        continue
                    out.append(
                        _suggestion(
                            str(ph),
                            str(ph),
                            stype="aspect_expansion",
                            insert_mode="append",
                            source="aspect",
                            aspect_id=aid,
                            aspect_label=label,
                            aspect_score=min(1.0, best / 100.0),
                        )
                    )
        return out[:10]


class UserStyleCandidateGenerator:
    def generate(
        self, state: TextInputState, user_profile: dict[str, Any] | None
    ) -> list[SuggestionCandidate]:
        if not user_profile:
            return []
        phrases = user_profile.get("common_phrases") or []
        out: list[SuggestionCandidate] = []
        ctx = state.text_before_cursor.lower()
        for ph in phrases[:25]:
            p = str(ph).strip()
            if len(p) < 4:
                continue
            if p.lower() in ctx:
                continue
            r = fuzz.partial_ratio(p.lower(), ctx[-40:])
            if r > 85:
                continue
            out.append(
                _suggestion(
                    p,
                    p,
                    stype="phrase_completion",
                    insert_mode="append",
                    source="user_style",
                    user_style_score=0.4,
                )
            )
        return out[:8]


class GenericFallbackCandidateGenerator:
    def generate(self, profile: dict[str, Any]) -> list[SuggestionCandidate]:
        starters = profile.get("generic_starters") or [
            "в целом",
            "по ощущениям",
            "для ежедневного использования",
            "есть небольшие нюансы",
            "за свою цену",
        ]
        return [
            _suggestion(
                s,
                s,
                stype="generic_fallback",
                insert_mode="append",
                source="generic",
                quality_score=0.4,
            )
            for s in starters
        ]


def merge_candidates(
    state: TextInputState,
    profile: dict[str, Any],
    user_profile: dict[str, Any] | None,
) -> list[SuggestionCandidate]:
    gens = [
        PrefixCandidateGenerator(),
        NgramCandidateGenerator(),
        DynamicAspectCandidateGenerator(),
        UserStyleCandidateGenerator(),
        GenericFallbackCandidateGenerator(),
    ]
    out: list[SuggestionCandidate] = []
    out.extend(gens[0].generate(state, profile))
    out.extend(gens[1].generate(state, profile))
    out.extend(gens[2].generate(state, profile))
    out.extend(gens[3].generate(state, user_profile))
    if len(out) < 3:
        out.extend(gens[4].generate(profile))
    return out
