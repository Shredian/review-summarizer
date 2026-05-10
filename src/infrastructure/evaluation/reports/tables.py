from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.domain.evaluation.dto import ComparisonReportDTO


FUNCTIONAL_COMPARISON_ROWS: list[dict[str, Any]] = [
    {
        "system": "Amazon",
        "overall_summary": True,
        "aspect_highlights": True,
        "pros_cons": True,
        "frequent_features": True,
        "evidence_grounding": False,
        "explainability": "low",
        "structured_artifacts": False,
        "analytics_ready": "medium",
    },
    {
        "system": "Wayfair",
        "overall_summary": True,
        "aspect_highlights": True,
        "pros_cons": True,
        "frequent_features": True,
        "evidence_grounding": False,
        "explainability": "low",
        "structured_artifacts": False,
        "analytics_ready": "medium",
    },
    {
        "system": "Walmart",
        "overall_summary": True,
        "aspect_highlights": True,
        "pros_cons": True,
        "frequent_features": True,
        "evidence_grounding": False,
        "explainability": "low",
        "structured_artifacts": False,
        "analytics_ready": "medium",
    },
    {
        "system": "Яндекс Маркет",
        "overall_summary": True,
        "aspect_highlights": True,
        "pros_cons": True,
        "frequent_features": True,
        "evidence_grounding": False,
        "explainability": "low",
        "structured_artifacts": False,
        "analytics_ready": "medium",
    },
    {
        "system": "aspect_evidence_guided_v1",
        "overall_summary": True,
        "aspect_highlights": True,
        "pros_cons": True,
        "frequent_features": True,
        "evidence_grounding": True,
        "explainability": "high",
        "structured_artifacts": True,
        "analytics_ready": "high",
    },
]


def functional_comparison_table() -> list[dict[str, Any]]:
    """Таблица §13 — наблюдаемые возможности + наша система."""
    return [dict(r) for r in FUNCTIONAL_COMPARISON_ROWS]


def write_comparison_report(report: ComparisonReportDTO, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    json_path = out_dir / "comparison_report.json"
    json_path.write_text(json.dumps(report.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    paths["json"] = str(json_path)

    csv_path = out_dir / "metric_table.csv"
    if report.table_rows:
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=sorted({k for row in report.table_rows for k in row}))
            w.writeheader()
            for row in report.table_rows:
                w.writerow(row)
        paths["csv"] = str(csv_path)

    func_path = out_dir / "functional_comparison.csv"
    func_rows = functional_comparison_table()
    with func_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(func_rows[0].keys()))
        w.writeheader()
        for row in func_rows:
            w.writerow(row)
    paths["functional_csv"] = str(func_path)

    return paths
