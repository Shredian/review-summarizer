from uuid import UUID

from src.domain.evaluation.config import EvaluationRunConfig
from src.domain.evaluation.dto import ReferenceAspectDTO, ReferenceEvidenceDTO
from src.infrastructure.evaluation.metrics.primary import (
    aspect_coverage_metrics,
    compute_primary_metrics,
    specificity_score,
)


def test_aspect_coverage_alias():
    aspects = [
        ReferenceAspectDTO(
            aspect_name="экран",
            aliases=["дисплей"],
            salience_weight=1.0,
            expected_polarity="positive",
            evidence_items=[],
        )
    ]
    uw, ww, d = aspect_coverage_metrics(aspects, "Очень яркий экран понравился", embed_model_name=None)
    assert uw == 1.0
    assert ww == 1.0
    assert d["missing_aspects"] == []


def test_specificity():
    aspects = [
        ReferenceAspectDTO(
            aspect_name="вентилятор",
            aliases=[],
            salience_weight=1.0,
            expected_polarity="negative",
            evidence_items=[],
        )
    ]
    s, _ = specificity_score("вентилятор шумит при нагрузке", aspects)
    assert s > 0.5


def test_compute_primary_smoke():
    aspects = [
        ReferenceAspectDTO(
            aspect_name="качество",
            aliases=[],
            salience_weight=0.6,
            expected_polarity="positive",
            evidence_items=[
                ReferenceEvidenceDTO(
                    review_id=UUID("00000000-0000-0000-0000-000000000001"),
                    text="качество сборки отличное",
                    section_type="plus",
                    polarity="positive",
                )
            ],
        )
    ]
    cfg = EvaluationRunConfig(benchmark_set_name="t")
    cfg.run_auxiliary_metrics = False
    m = compute_primary_metrics(
        aspects,
        {"text_overall": "Качество сборки хорошее.", "text_pros": "качество отличное"},
        cfg,
    )
    names = {x.metric_name for x in m}
    assert "aspect_coverage_weighted" in names
    assert "overall_score_weighted" in names
