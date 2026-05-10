from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover
    plt = None

from src.domain.evaluation.dto import ComparisonReportDTO

from src.utils.logger import logger


def render_bar_chart_metric_aggregate(
    aggregates: dict[str, dict[str, float]],
    out_path: Path,
    *,
    title: str = "Основные метрики по системам",
) -> str | None:
    """Bar chart по средним primary метрикам."""
    if plt is None:
        logger.warning("matplotlib не установлен, график пропущен")
        return None
    systems = list(aggregates.keys())
    metric_names = sorted({k for sys in aggregates for k in aggregates[sys]})
    if not systems or not metric_names:
        return None
    x = range(len(metric_names))
    width = 0.8 / max(len(systems), 1)
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, sys in enumerate(systems):
        vals = [aggregates[sys].get(m, 0.0) for m in metric_names]
        ax.bar([xi + i * width for xi in x], vals, width=width, label=sys)
    ax.set_xticks([xi + width * (len(systems) - 1) / 2 for xi in x])
    ax.set_xticklabels(metric_names, rotation=30, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return str(out_path)


def build_aggregate_table_rows(
    per_result_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, float]]]:
    """Агрегация по system_name средним для chart."""
    from collections import defaultdict

    sums: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in per_result_rows:
        sys = str(row.get("system_name", ""))
        metrics = row.get("metrics", {})
        if not isinstance(metrics, dict):
            continue
        for k, v in metrics.items():
            if isinstance(v, bool):
                continue
            if v is None:
                continue
            try:
                sums[sys][k].append(float(v))
            except (TypeError, ValueError):
                continue
    table_rows: list[dict[str, Any]] = []
    ag: dict[str, dict[str, float]] = {}
    for sys, mmap in sums.items():
        ag[sys] = {}
        flat: dict[str, Any] = {"system_name": sys}
        for m, lst in mmap.items():
            if not lst:
                continue
            avg = sum(lst) / len(lst)
            flat[m] = avg
            ag[sys][m] = avg
        table_rows.append(flat)
    return table_rows, ag
