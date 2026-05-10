from src.infrastructure.evaluation.metrics.primary import (
    compute_primary_metrics,
    flatten_summary_text,
)

__all__ = [
    "build_reference_text_from_ledger",
    "compute_auxiliary_metrics",
    "compute_primary_metrics",
    "flatten_summary_text",
]


def compute_auxiliary_metrics(*args, **kwargs):  # type: ignore[no-untyped-def]
    from src.infrastructure.evaluation.metrics.auxiliary import (
        compute_auxiliary_metrics as _compute_auxiliary_metrics,
    )

    return _compute_auxiliary_metrics(*args, **kwargs)


def build_reference_text_from_ledger(*args, **kwargs):  # type: ignore[no-untyped-def]
    from src.infrastructure.evaluation.metrics.auxiliary import (
        build_reference_text_from_ledger as _build,
    )

    return _build(*args, **kwargs)
