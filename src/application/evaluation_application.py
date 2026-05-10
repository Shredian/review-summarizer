from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.domain.evaluation.config import EvaluationRunConfig
from src.domain.evaluation.dto import ComparisonReportDTO
from src.domain.models.summary import Summary
from src.domain.services.summarization_service import SummarizationService
from src.infrastructure.clients.openai_client import OpenAIClient
from src.infrastructure.db.models.evaluation_result import EvaluationResultDB
from src.infrastructure.db.models.evaluation_run import EvaluationRunDB
from src.infrastructure.db.models.generated_summary_snapshot import GeneratedSummarySnapshotDB
from src.infrastructure.db.models.reference_ledger import ReferenceLedgerDB
from src.infrastructure.db.repositories.benchmark_catalog_repository import (
    BenchmarkCatalogRepository,
)
from src.infrastructure.db.repositories.evaluation_run_repository import EvaluationRunRepository
from src.infrastructure.db.repositories.reference_ledger_repository import ReferenceLedgerRepository
from src.infrastructure.db.repositories.summary_plan_repository import SummaryPlanRepository
from src.infrastructure.db.repositories.summary_repository import SummaryRepository
from src.infrastructure.evaluation.benchmark_runtime_sync import sync_benchmark_to_main_tables
from src.infrastructure.evaluation.glass_box import glass_box_from_plan
from src.infrastructure.evaluation.ingestion.json_loader import (
    BenchmarkBundleRecord,
    export_snapshot_jsonl,
    load_benchmark_catalog_from_json,
    parse_benchmark_catalog_json,
)
from src.infrastructure.evaluation.ledger_dto import ledger_orm_to_aspect_dtos
from src.infrastructure.evaluation.llm_judge.service import EvaluationLLMJudge
from src.infrastructure.evaluation.metrics.auxiliary import (
    build_reference_text_from_ledger,
    compute_auxiliary_metrics,
)
from src.infrastructure.evaluation.metrics.primary import compute_primary_metrics
from src.infrastructure.evaluation.reference_ledger.builder import (
    benchmark_reviews_to_domain,
    build_reference_ledger_from_benchmark,
)
from src.infrastructure.evaluation.reports.charts import (
    build_aggregate_table_rows,
    render_bar_chart_metric_aggregate,
)
from src.infrastructure.evaluation.reports.tables import write_comparison_report
from src.utils.logger import logger


def summary_to_eval_dict(summary: Summary) -> dict[str, Any]:
    return {
        "text_overall": summary.text_overall,
        "text_neutral": summary.text_neutral,
        "text_pros": summary.text_pros,
        "text_cons": summary.text_cons,
        "key_phrases": [kp.model_dump() for kp in summary.key_phrases]
        if summary.key_phrases
        else None,
    }


def external_snapshot_to_eval_dict(ext: Any) -> dict[str, Any]:
    return {
        "summary_text": ext.summary_text,
        "text_pros": ext.pros_text,
        "text_cons": ext.cons_text,
    }


def _metric_list_to_nested(metrics: list[Any]) -> dict[str, Any]:
    primary: dict[str, Any] = {}
    details: dict[str, Any] = {}
    for m in metrics:
        primary[m.metric_name] = m.value
        if getattr(m, "details_json", None):
            details[m.metric_name] = m.details_json
    return {"flat": primary, "details": details}


def _aspect_lines_for_judge(aspects: list[Any], top_k: int) -> list[str]:
    lines: list[str] = []
    for a in aspects:
        evs = " | ".join([e.text for e in a.evidence_items[:top_k]])
        lines.append(
            f"- {a.aspect_name} (expected {a.expected_polarity}, salience {a.salience_weight:.3f}): {evs}"
        )
    return lines


@dataclass
class EvaluationRunSummary:
    run_id: UUID
    artifacts_dir: str | None = None


class EvaluationApplication:
    """Оркестрация benchmark ingest, ledger, суммаризация, метрики, judge, отчёты."""

    def __init__(
        self,
        session_factory: sessionmaker[AsyncSession],
        benchmark_catalog_repository: BenchmarkCatalogRepository,
        reference_ledger_repository: ReferenceLedgerRepository,
        evaluation_run_repository: EvaluationRunRepository,
        summarization_service: SummarizationService,
        summary_repository: SummaryRepository,
        summary_plan_repository: SummaryPlanRepository,
        openai_client: OpenAIClient | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._benchmarks = benchmark_catalog_repository
        self._ledgers = reference_ledger_repository
        self._runs = evaluation_run_repository
        self._summarization = summarization_service
        self._summaries = summary_repository
        self._plans = summary_plan_repository
        self._judge = EvaluationLLMJudge(openai_client)

    async def ingest_json_catalog(self, path: Path | str) -> list[UUID]:
        bundles = load_benchmark_catalog_from_json(path)
        ids: list[UUID] = []
        for b in bundles:
            pid = await self._benchmarks.upsert_benchmark_bundle(
                b.product,
                b.reviews,
                b.external,
            )
            ids.append(pid)
        return ids

    async def ingest_json_catalog_text(self, raw: str) -> list[UUID]:
        bundles = parse_benchmark_catalog_json(raw, label="streamlit/catalog_text")
        ids: list[UUID] = []
        for b in bundles:
            pid = await self._benchmarks.upsert_benchmark_bundle(
                b.product,
                b.reviews,
                b.external,
            )
            ids.append(pid)
        return ids

    async def list_benchmark_sets_overview(self) -> list[tuple[str, int]]:
        return await self._benchmarks.list_benchmark_sets_overview()

    async def export_benchmark_jsonl(self, benchmark_set_name: str, out_path: Path | str) -> None:
        products = await self._benchmarks.list_products_by_set_deep(benchmark_set_name)
        bundles: list[BenchmarkBundleRecord] = []
        for p in products:
            ext = p.external_summaries[0] if p.external_summaries else None
            bundles.append(
                BenchmarkBundleRecord(
                    product=p,
                    reviews=list(p.reviews),
                    external=ext,
                )
            )
        export_snapshot_jsonl(bundles, out_path)

    async def ensure_reference_ledger(
        self,
        product_id: UUID,
        config: EvaluationRunConfig,
        *,
        reference_version: str = "ledger_v1_draft",
        force_rebuild: bool = False,
    ) -> ReferenceLedgerDB:
        if not force_rebuild:
            existing = await self._ledgers.get_latest_ledger_deep(product_id)
            if existing:
                return existing
        deep = await self._benchmarks.get_product_deep(product_id)
        ledger, aspects, ev_matrix = build_reference_ledger_from_benchmark(
            deep,
            list(deep.reviews),
            reference_version=reference_version,
            config=config,
        )
        await self._ledgers.save_ledger_tree(ledger, aspects, ev_matrix)
        saved = await self._ledgers.get_ledger_deep(ledger.id)
        return saved

    async def run_evaluation_for_set(
        self,
        config: EvaluationRunConfig,
        *,
        run_name: str | None = None,
        export_dir: Path | None = None,
        force_ledger_rebuild: bool = False,
        product_limit: int | None = None,
    ) -> EvaluationRunSummary:
        run_id = uuid4()
        name = run_name or f"eval_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        run_row = EvaluationRunDB(
            id=run_id,
            benchmark_set_name=config.benchmark_set_name,
            run_name=name,
            created_at=datetime.now(UTC),
            config_json=config.model_dump(mode="json"),
        )
        await self._runs.create_run(run_row)

        products = await self._benchmarks.list_products_by_set_deep(
            config.benchmark_set_name,
            limit=product_limit,
        )
        results: list[EvaluationResultDB] = []
        table_rows_accum: list[dict[str, Any]] = []

        for prod in products:
            ledger = await self.ensure_reference_ledger(
                prod.id,
                config,
                force_rebuild=force_ledger_rebuild,
            )
            aspect_dtos = ledger_orm_to_aspect_dtos(ledger)
            ref_lines = _aspect_lines_for_judge(aspect_dtos, config.evidence_top_k_for_judge)
            ref_text = build_reference_text_from_ledger(
                [a.aspect_name for a in aspect_dtos],
                [e.text for a in aspect_dtos for e in a.evidence_items],
            )

            await sync_benchmark_to_main_tables(self._session_factory, prod, list(prod.reviews))
            domain_reviews = benchmark_reviews_to_domain(prod, prod.reviews)
            summary = await self._summarization.summarize(
                product_id=str(prod.id),
                reviews=domain_reviews,
                method_code=config.method_code,
                params=config.summarization_params,
            )
            sid = await self._summaries.create(summary)
            summary.id = sid
            method = self._summarization.get_method(config.method_code)
            await method.persist_artifacts(summary)

            gen_row = GeneratedSummarySnapshotDB(
                id=uuid4(),
                benchmark_product_id=prod.id,
                method_name=summary.method,
                method_version=summary.method_version,
                summary_id=sid,
                text_overall=summary.text_overall,
                text_pros=summary.text_pros,
                text_cons=summary.text_cons,
                text_neutral=summary.text_neutral,
                key_phrases_json=[kp.model_dump() for kp in summary.key_phrases]
                if summary.key_phrases
                else None,
            )
            await self._benchmarks.add_generated_snapshot(gen_row)

            our_dict = summary_to_eval_dict(summary)
            ext = prod.external_summaries[0] if prod.external_summaries else None
            ext_dict = external_snapshot_to_eval_dict(ext) if ext else {"summary_text": ""}

            our_metrics = compute_primary_metrics(aspect_dtos, our_dict, config)
            ext_metrics = compute_primary_metrics(aspect_dtos, ext_dict, config)
            aux_our = (
                compute_auxiliary_metrics(our_dict, ref_text, config)
                if config.run_auxiliary_metrics
                else []
            )
            aux_ext = (
                compute_auxiliary_metrics(ext_dict, ref_text, config)
                if config.run_auxiliary_metrics
                else []
            )

            glass_our: list[Any] = []
            if config.run_glass_box and sid:
                plan = await self._plans.get_by_summary(sid)
                glass_our = glass_box_from_plan(plan, our_dict)

            judge_our = None
            judge_ext = None
            judge_pair = None
            if config.run_llm_judge:
                flat_our = "\n".join(
                    x for x in (our_dict.get("text_overall"), our_dict.get("text_pros")) if x
                )
                flat_ext = ext_dict.get("summary_text") or ""
                judge_our = await self._judge.score_rubric(
                    candidate_summary=flat_our or "",
                    aspect_reference_lines=ref_lines,
                    product_title=prod.product_title,
                )
                judge_ext = await self._judge.score_rubric(
                    candidate_summary=flat_ext or "",
                    aspect_reference_lines=ref_lines,
                    product_title=prod.product_title,
                )
                if config.run_pairwise_judge and flat_ext.strip():
                    judge_pair = await self._judge.pairwise_with_swap(
                        our_summary=flat_our or "",
                        external_summary=flat_ext,
                        aspect_reference_lines=ref_lines,
                        product_title=prod.product_title,
                    )

            def build_metrics_nested(
                primary: list[Any], aux: list[Any], glass: list[Any]
            ) -> dict[str, Any]:
                nested = _metric_list_to_nested(primary)
                if aux:
                    nested["auxiliary"] = _metric_list_to_nested(aux)["flat"]
                if glass:
                    nested["glass_box"] = _metric_list_to_nested(glass)["flat"]
                return nested

            our_notes: dict[str, Any] = {}
            if judge_our is not None:
                our_notes["judge_rubric"] = judge_our.model_dump()
            ext_notes: dict[str, Any] = {}
            if judge_ext is not None:
                ext_notes["judge_rubric"] = judge_ext.model_dump()

            our_result = EvaluationResultDB(
                id=uuid4(),
                evaluation_run_id=run_id,
                benchmark_product_id=prod.id,
                system_name="our_method",
                metrics_json=build_metrics_nested(our_metrics, aux_our, glass_our),
                judge_scores_json=judge_pair,
                notes_json=our_notes or None,
            )
            ext_result = EvaluationResultDB(
                id=uuid4(),
                evaluation_run_id=run_id,
                benchmark_product_id=prod.id,
                system_name="external_platform",
                metrics_json=build_metrics_nested(ext_metrics, aux_ext, []),
                judge_scores_json=None,
                notes_json=ext_notes or None,
            )
            results.extend([our_result, ext_result])

            table_rows_accum.append(
                {
                    "benchmark_product_id": str(prod.id),
                    "system_name": "our_method",
                    "metrics": our_result.metrics_json.get("flat", {}),
                }
            )
            table_rows_accum.append(
                {
                    "benchmark_product_id": str(prod.id),
                    "system_name": "external_platform",
                    "metrics": ext_result.metrics_json.get("flat", {}),
                }
            )

        await self._runs.add_results(results)

        art_path: str | None = None
        if export_dir is not None:
            agg_rows, ag = build_aggregate_table_rows(table_rows_accum)
            chart = render_bar_chart_metric_aggregate(
                ag,
                export_dir / "metrics_bar.png",
            )
            report = ComparisonReportDTO(
                benchmark_name=config.benchmark_set_name,
                systems=list({r.system_name for r in results}),
                table_rows=agg_rows,
                aggregate_scores=ag,
                chart_paths=[chart] if chart else [],
            )
            paths = write_comparison_report(report, export_dir)
            art_path = paths.get("json")

        logger.info("Evaluation run завершён: {}", run_id)
        return EvaluationRunSummary(run_id=run_id, artifacts_dir=art_path)
