"""REST hooks для запуска evaluation (опционально)."""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.application.evaluation_application import EvaluationApplication, EvaluationRunSummary
from src.container import Container
from src.domain.evaluation.config import EvaluationRunConfig

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


def get_evaluation_app() -> EvaluationApplication:
    return Container().evaluation_application()


class EvaluationRunRequest(BaseModel):
    benchmark_set_name: str
    run_name: str | None = None
    export_dir: str | None = Field(
        default=None,
        description="Каталог для JSON/CSV отчёта (на сервере)",
    )
    force_ledger_rebuild: bool = False
    run_llm_judge: bool = True
    run_auxiliary_metrics: bool = True
    run_glass_box: bool = False
    product_limit: int | None = Field(
        default=None,
        ge=1,
        le=500,
        description="Ограничить число товаров набором LIMIT (меньше нагрузка на память)",
    )


class EvaluationRunResponse(BaseModel):
    run_id: UUID
    artifacts_path: str | None = None


@router.post("/run", response_model=EvaluationRunResponse)
async def run_evaluation(
    body: EvaluationRunRequest,
    app: EvaluationApplication = Depends(get_evaluation_app),
) -> EvaluationRunResponse:
    export = Path(body.export_dir) if body.export_dir else None
    if export is not None:
        export.mkdir(parents=True, exist_ok=True)
    cfg = EvaluationRunConfig(
        benchmark_set_name=body.benchmark_set_name,
        run_llm_judge=body.run_llm_judge,
        run_pairwise_judge=body.run_llm_judge,
        run_auxiliary_metrics=body.run_auxiliary_metrics,
        run_glass_box=body.run_glass_box,
    )
    try:
        result: EvaluationRunSummary = await app.run_evaluation_for_set(
            cfg,
            run_name=body.run_name,
            export_dir=export,
            force_ledger_rebuild=body.force_ledger_rebuild,
            product_limit=body.product_limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return EvaluationRunResponse(run_id=result.run_id, artifacts_path=result.artifacts_dir)
