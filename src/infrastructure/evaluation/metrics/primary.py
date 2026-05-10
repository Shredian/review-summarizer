from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from src.domain.evaluation.config import EvaluationRunConfig
from src.domain.evaluation.dto import ClaimDTO, MetricResultDTO, ReferenceAspectDTO


def _np():  # pragma: no cover - optional heavy dep
    try:
        import numpy as np

        return np
    except ImportError:
        return None


def flatten_summary_text(summary: dict[str, Any]) -> str:
    """Склеивает поля summary в один текст для метрик."""
    parts: list[str] = []
    for key in ("text_overall", "text_neutral", "text_pros", "text_cons", "summary_text"):
        v = summary.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    kp = summary.get("key_phrases")
    if isinstance(kp, list):
        for item in kp:
            if isinstance(item, dict) and item.get("phrase"):
                parts.append(str(item["phrase"]))
    return "\n".join(parts)


def split_claims(text: str) -> list[str]:
    """Грубое разбиение на атомарные утверждения (по предложениям)."""
    cleaned = text.strip()
    if not cleaned:
        return []
    chunks = re.split(r"(?<=[.!?])\s+", cleaned)
    return [c.strip() for c in chunks if len(c.strip()) > 3]


def extract_claims_dto(text: str) -> list[ClaimDTO]:
    return [ClaimDTO(text=c) for c in split_claims(text)]


def _normalize_weights(weights: list[float]) -> list[float]:
    s = float(sum(weights))
    if s <= 0:
        n = max(len(weights), 1)
        return [1.0 / n] * len(weights)
    return [float(w) / s for w in weights]


def _weighted_dot(weights: list[float], flags: list[bool]) -> float:
    return sum(weights[i] * (1.0 if flags[i] else 0.0) for i in range(len(flags)))


def _cosine_sim_matrix_np(a: Any, b: Any) -> Any:
    np = _np()
    if np is None:
        raise RuntimeError("numpy required for embedding similarity")
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return a_norm @ b_norm.T


def aspect_coverage_metrics(
    aspects: list[ReferenceAspectDTO],
    summary_text: str,
    *,
    embed_model_name: str | None = None,
    embedding_threshold: float = 0.72,
) -> tuple[float, float, dict[str, Any]]:
    """Unweighted and salience-weighted coverage."""
    if not aspects:
        return 1.0, 1.0, {"covered": [], "missing": []}
    lowered = summary_text.lower()
    covered_flags: list[bool] = []
    embedder = None
    if embed_model_name and _np() is not None:
        try:
            from src.infrastructure.services.summarization.aspect_evidence_guided.embedding_cache import (
                get_shared_sentence_transformer,
            )

            embedder = get_shared_sentence_transformer(embed_model_name)
        except Exception:
            embedder = None

    sims: list[float | None] = [None] * len(aspects)
    for i, a in enumerate(aspects):
        names = [a.aspect_name.lower(), *[x.lower() for x in a.aliases]]
        hit = any(n and n in lowered for n in names if n)
        if hit:
            covered_flags.append(True)
            continue
        if embedder is not None and summary_text.strip() and _np() is not None:
            try:
                np = _np()
                labels = [a.aspect_name] + list(a.aliases)
                emb_sum = embedder.encode([summary_text])
                emb_lbl = embedder.encode(labels)
                sims_mat = _cosine_sim_matrix_np(emb_lbl, emb_sum)
                sim = float(np.max(sims_mat))
                sims[i] = sim
                covered_flags.append(sim >= embedding_threshold)
            except Exception:
                covered_flags.append(False)
        else:
            covered_flags.append(False)

    unweighted = sum(1 for c in covered_flags if c) / len(aspects)
    weights = _normalize_weights([a.salience_weight for a in aspects])
    weighted = _weighted_dot(weights, covered_flags)

    missing = [aspects[j].aspect_name for j, c in enumerate(covered_flags) if not c]
    return unweighted, weighted, {
        "covered_mask": covered_flags,
        "missing_aspects": missing,
        "max_alias_similarity": sims,
    }


def polarity_in_summary_for_aspect(
    aspect: ReferenceAspectDTO,
    summary: dict[str, Any],
    flat: str,
) -> str | None:
    """Грубая эвристика полярности упоминания аспекта в структурированном summary."""
    low = flat.lower()
    names = [aspect.aspect_name.lower()] + [x.lower() for x in aspect.aliases]
    names = [n for n in names if n]

    def contains_in(text: str | None) -> bool:
        if not text:
            return False
        t = text.lower()
        return any(n in t for n in names)

    in_pros = contains_in(summary.get("text_pros"))
    in_cons = contains_in(summary.get("text_cons"))
    in_neg = contains_in(summary.get("text_neutral"))
    in_overall = contains_in(summary.get("text_overall"))

    if in_pros and not in_cons:
        return "positive"
    if in_cons and not in_pros:
        return "negative"
    if in_pros and in_cons:
        return "mixed"
    if in_overall or in_neg:
        frag = ""
        if summary.get("text_overall"):
            frag = summary["text_overall"].lower()
        elif summary.get("text_neutral"):
            frag = summary["text_neutral"].lower()
        pos_hits = sum(1 for n in names if n and any(p in frag for p in ("хорош", "отлич", "нрав", "+")))
        neg_hits = sum(1 for n in names if n and any(p in frag for p in ("плох", "ужас", "минус")))
        if pos_hits > neg_hits:
            return "positive"
        if neg_hits > pos_hits:
            return "negative"
    return None


def sentiment_consistency_score(
    aspects: list[ReferenceAspectDTO],
    summary: dict[str, Any],
    flat: str,
    coverage_mask: list[bool] | None = None,
) -> tuple[float, dict[str, Any]]:
    """Согласованность тональности по покрытым аспектам (0..1)."""
    scores: list[float] = []
    details: dict[str, Any] = {"per_aspect": []}
    for idx, a in enumerate(aspects):
        if coverage_mask is not None and idx < len(coverage_mask) and not coverage_mask[idx]:
            continue
        exp = (a.expected_polarity or "").lower()
        got = polarity_in_summary_for_aspect(a, summary, flat)
        if got is None:
            continue
        if exp == got:
            scores.append(1.0)
        elif {exp, got} == {"positive", "negative"}:
            scores.append(0.0)
        else:
            scores.append(0.5)
        details["per_aspect"].append(
            {"aspect": a.aspect_name, "expected": exp, "summary_polarity": got}
        )
    if not scores:
        return 1.0, details
    return float(sum(scores) / len(scores)), details


def evidence_support_rates(
    claims: list[str],
    evidence_texts: list[str],
    threshold: float = 0.55,
    embed_model_name: str | None = None,
) -> tuple[float, float, dict[str, Any]]:
    """Доли поддержанных / неподдержанных claims (эмбеддинги если доступны)."""
    if not claims:
        return 1.0, 0.0, {"supported": 0, "total": 0}
    texts = [t for t in evidence_texts if t and t.strip()]
    if not texts:
        return 0.0, 1.0, {"supported": 0, "total": len(claims), "note": "no_evidence"}
    embedder = None
    if embed_model_name and _np() is not None:
        try:
            from src.infrastructure.services.summarization.aspect_evidence_guided.embedding_cache import (
                get_shared_sentence_transformer,
            )

            embedder = get_shared_sentence_transformer(embed_model_name)
        except Exception:
            embedder = None

    supported = 0
    per_claim: list[dict[str, Any]] = []
    if embedder is not None and _np() is not None:
        try:
            np = _np()
            ce = embedder.encode(claims)
            te = embedder.encode(texts)
            sims = _cosine_sim_matrix_np(ce, te)
            best = sims.max(axis=1)
            for i, claim in enumerate(claims):
                ok = float(best[i]) >= threshold
                supported += int(ok)
                per_claim.append({"claim": claim, "best_sim": float(best[i]), "supported": ok})
        except Exception:
            embedder = None
    if embedder is None:
        low_claims = [c.lower() for c in claims]
        low_ev = [t.lower() for t in texts]
        for claim in low_claims:
            ok = any(
                sum(1 for w in claim.split() if len(w) > 3 and w in ev) >= 2 for ev in low_ev
            )
            supported += int(ok)
            per_claim.append({"claim": claim, "supported": ok})
    rate = supported / len(claims)
    return rate, 1.0 - rate, {"supported": supported, "total": len(claims), "claims": per_claim}


def specificity_score(summary_text: str, aspects: list[ReferenceAspectDTO]) -> tuple[float, dict[str, Any]]:
    """Эвристика специфичности: доля «содержательных» токенов + совпадение с аспектами."""
    if not summary_text.strip():
        return 0.0, {}
    toks = [t for t in re.split(r"\s+", summary_text.lower()) if len(t) > 2]
    if not toks:
        return 0.0, {}
    generic = {
        "хороший",
        "плохой",
        "норм",
        "нормальный",
        "качество",
        "товар",
        "отзыв",
        "рекоменд",
        "стоит",
    }
    content = [t for t in toks if t not in generic]
    lex_score = len(content) / len(toks)
    aspect_hits = 0
    for a in aspects:
        if a.aspect_name.lower() in summary_text.lower():
            aspect_hits += 1
            continue
        if any(al.lower() in summary_text.lower() for al in a.aliases):
            aspect_hits += 1
    asp_score = min(1.0, aspect_hits / max(len(aspects), 1)) if aspects else 0.5
    score = 0.6 * lex_score + 0.4 * asp_score
    return float(score), {"lexical_specificity": lex_score, "aspect_hit_rate": asp_score}


def aspect_balance_score(
    aspects: list[ReferenceAspectDTO],
    summary_text: str,
    embed_model_name: str | None = None,  # noqa: ARG001 - API совместимость
) -> tuple[float, dict[str, Any]]:
    """1 - нормированный Jensen–Shannon между распределениями salience и упоминаний в summary."""
    if not aspects or not summary_text.strip():
        return 1.0, {}
    p = _normalize_weights([a.salience_weight for a in aspects])
    mention_counts: list[float] = []
    low = summary_text.lower()
    for a in aspects:
        hits = low.count(a.aspect_name.lower())
        for al in a.aliases:
            hits += low.count(al.lower())
        mention_counts.append(float(hits) + 1e-3)
    q = _normalize_weights(mention_counts)
    try:
        from scipy.spatial.distance import jensenshannon

        js = float(jensenshannon(p, q, base=2.0))
        if math.isnan(js):
            js = 0.0
    except Exception:
        js = sum(abs(p[i] - q[i]) for i in range(len(p)))

    score = max(0.0, 1.0 - js)
    return score, {"js_divergence": js, "source_dist": list(p), "summary_dist": list(q)}


def non_redundancy_score(
    summary_text: str,
    embed_model_name: str | None = None,
) -> tuple[float, dict[str, Any]]:
    """Доля уникальных семантических кластеров среди предложений."""
    sents = split_claims(summary_text.replace("\n", " "))
    if len(sents) <= 1:
        return 1.0, {"unique_ratio": 1.0}
    embedder = None
    if embed_model_name and _np() is not None:
        try:
            from src.infrastructure.services.summarization.aspect_evidence_guided.embedding_cache import (
                get_shared_sentence_transformer,
            )

            embedder = get_shared_sentence_transformer(embed_model_name)
        except Exception:
            embedder = None
    if embedder is None or _np() is None:
        uniq = len({s.lower() for s in sents})
        return uniq / len(sents), {"unique_ratio": uniq / len(sents)}
    try:
        emb = embedder.encode(sents)
        sim = _cosine_sim_matrix_np(emb, emb)
        clusters = 0
        used = [False] * len(sents)
        threshold = 0.92
        for i in range(len(sents)):
            if used[i]:
                continue
            clusters += 1
            used[i] = True
            for j in range(i + 1, len(sents)):
                if not used[j] and float(sim[i, j]) >= threshold:
                    used[j] = True
        ratio = clusters / len(sents)
        return float(ratio), {"clusters": clusters, "unique_ratio": ratio}
    except Exception:
        uniq = len({s.lower() for s in sents})
        return uniq / len(sents), {"unique_ratio": uniq / len(sents)}


def compute_primary_metrics(
    aspects: list[ReferenceAspectDTO],
    summary: dict[str, Any],
    config: EvaluationRunConfig,
) -> list[MetricResultDTO]:
    flat = flatten_summary_text(summary)
    evidence_texts: list[str] = []
    for a in aspects:
        for e in a.evidence_items:
            evidence_texts.append(e.text)

    uw, ww, cov_detail = aspect_coverage_metrics(
        aspects,
        flat,
        embed_model_name=config.embedding_model_name,
        embedding_threshold=config.aspect_match_embedding_threshold,
    )
    sent, sent_detail = sentiment_consistency_score(
        aspects,
        summary,
        flat,
        coverage_mask=cov_detail.get("covered_mask"),
    )
    claims_objs = extract_claims_dto(flat)
    claims = [c.text for c in claims_objs]
    sup_rate, unsup_rate, ev_detail = evidence_support_rates(
        claims,
        evidence_texts,
        threshold=config.claim_similarity_threshold,
        embed_model_name=config.embedding_model_name,
    )
    spec, spec_detail = specificity_score(flat, aspects)
    bal, bal_detail = aspect_balance_score(
        aspects,
        flat,
        embed_model_name=config.embedding_model_name,
    )
    nred, nred_detail = non_redundancy_score(flat, embed_model_name=config.embedding_model_name)

    w = config.overall_weights.normalized()
    overall = (
        w.aspect_coverage * ww
        + w.sentiment_consistency * sent
        + w.evidence_support_rate * sup_rate
        + w.specificity * spec
        + w.non_redundancy * nred
    )

    return [
        MetricResultDTO(metric_name="aspect_coverage_unweighted", value=uw, details_json=cov_detail),
        MetricResultDTO(metric_name="aspect_coverage_weighted", value=ww, details_json=cov_detail),
        MetricResultDTO(metric_name="sentiment_consistency", value=sent, details_json=sent_detail),
        MetricResultDTO(metric_name="evidence_support_rate", value=sup_rate, details_json=ev_detail),
        MetricResultDTO(metric_name="unsupported_claim_rate", value=unsup_rate, details_json=ev_detail),
        MetricResultDTO(metric_name="specificity", value=spec, details_json=spec_detail),
        MetricResultDTO(metric_name="aspect_balance_alignment", value=bal, details_json=bal_detail),
        MetricResultDTO(metric_name="non_redundancy", value=nred, details_json=nred_detail),
        MetricResultDTO(
            metric_name="overall_score_weighted",
            value=float(overall),
            details_json={"weights": w.model_dump()},
        ),
    ]
