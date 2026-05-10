from __future__ import annotations

from typing import Any

from src.domain.evaluation.config import EvaluationRunConfig
from src.domain.evaluation.dto import MetricResultDTO
from src.infrastructure.evaluation.metrics.primary import flatten_summary_text

from src.utils.logger import logger


def _pseudo_reference_from_aspects(reference_dump: str) -> str:
    return reference_dump.strip()


def compute_auxiliary_metrics(
    summary: dict[str, Any],
    reference_flat: str,
    config: EvaluationRunConfig,
) -> list[MetricResultDTO]:
    """BERTScore / ROUGE / embedding similarity — ленивые зависимОсти."""
    if not config.run_auxiliary_metrics:
        return []
    results: list[MetricResultDTO] = []
    cand = flatten_summary_text(summary)
    ref = reference_flat.strip()
    if not cand or not ref:
        return [
            MetricResultDTO(
                metric_name="bertscore_f1",
                value=None,
                details_json={"skipped": "empty_text"},
            )
        ]

    try:
        from bert_score import score as bert_score  # type: ignore[import-untyped]

        preds = [cand]
        refs = [ref]
        p, r, f1 = bert_score(preds, refs, lang="en", model_type=config.bert_score_model)
        results.append(
            MetricResultDTO(
                metric_name="bertscore_precision",
                value=float(p.mean().item()),
                details_json={},
            )
        )
        results.append(
            MetricResultDTO(
                metric_name="bertscore_recall",
                value=float(r.mean().item()),
                details_json={},
            )
        )
        results.append(
            MetricResultDTO(
                metric_name="bertscore_f1",
                value=float(f1.mean().item()),
                details_json={"model": config.bert_score_model},
            )
        )
    except Exception as exc:  # pragma: no cover - heavy optional deps
        logger.warning("BERTScore недоступен: {}", exc)
        results.append(
            MetricResultDTO(
                metric_name="bertscore_f1",
                value=None,
                details_json={"error": str(exc)},
            )
        )

    try:
        from rouge_score import rouge_scorer  # type: ignore[import-untyped]

        scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)
        scores = scorer.score(ref, cand)
        results.append(
            MetricResultDTO(
                metric_name="rouge_l_f1",
                value=float(scores["rougeL"].fmeasure),
                details_json={
                    "precision": float(scores["rougeL"].precision),
                    "recall": float(scores["rougeL"].recall),
                },
            )
        )
    except Exception as exc:  # pragma: no cover
        logger.debug("ROUGE-L пропущен: {}", exc)
        results.append(
            MetricResultDTO(metric_name="rouge_l_f1", value=None, details_json={"skipped": str(exc)})
        )

    try:
        from src.infrastructure.services.summarization.aspect_evidence_guided.embedding_cache import (
            get_shared_sentence_transformer,
        )

        embedder = get_shared_sentence_transformer(config.embedding_model_name)
        if embedder is not None:
            e1 = embedder.encode([cand])
            e2 = embedder.encode([ref])
            sim = float((e1 @ e2.T)[0, 0] / (float((e1 * e1).sum() ** 0.5 * (e2 * e2).sum() ** 0.5) + 1e-9))
            results.append(
                MetricResultDTO(
                    metric_name="embedding_cosine_reference",
                    value=sim,
                    details_json={"model": config.embedding_model_name},
                )
            )
    except Exception as exc:  # pragma: no cover
        logger.debug("Embedding similarity пропущен: {}", exc)

    return results


def build_reference_text_from_ledger(
    aspect_lines: list[str],
    evidence_snippets: list[str],
) -> str:
    """Детерминированный псевдо-reference для auxiliary метрик."""
    lines = ["Aspects:", *aspect_lines, "Evidence:", *evidence_snippets[:50]]
    return _pseudo_reference_from_aspects("\n".join(lines))
