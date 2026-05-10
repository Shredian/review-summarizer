from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from src.infrastructure.db.models.benchmark_product import BenchmarkProductDB
from src.infrastructure.db.models.benchmark_review import BenchmarkReviewDB
from src.infrastructure.db.models.external_summary_snapshot import ExternalSummarySnapshotDB
from src.utils.logger import logger


class BenchmarkReviewRecord(BaseModel):
    """Одна строка отзыва во входном JSON."""

    id: UUID | None = None
    review_external_id: str | None = None
    rating: float | None = None
    title: str | None = None
    plus: str | None = None
    minus: str | None = None
    comment: str | None = None
    review_date: datetime | None = None
    source_url: str | None = None

    @field_validator("review_date", mode="before")
    @classmethod
    def parse_dt(cls, v: Any) -> datetime | None:
        if v is None or v == "":
            return None
        if isinstance(v, datetime):
            return v if v.tzinfo else v.replace(tzinfo=UTC)
        if isinstance(v, str):
            try:
                parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                return None
        return None


class ExternalSummaryRecord(BaseModel):
    summary_text: str
    pros_text: str | None = None
    cons_text: str | None = None
    highlights: list[Any] | None = None
    raw_block: dict[str, Any] | None = None


class BenchmarkProductRecord(BaseModel):
    """Один товар во входном каталоге."""

    id: UUID | None = None
    benchmark_set_name: str
    platform_name: str
    product_external_id: str | None = None
    product_title: str
    product_url: str | None = None
    snapshot_timestamp: datetime
    category: str | None = None
    notes: str | None = None
    reviews: list[BenchmarkReviewRecord] = Field(default_factory=list)
    external_summary: ExternalSummaryRecord | None = None

    @field_validator("snapshot_timestamp", mode="before")
    @classmethod
    def parse_snap(cls, v: Any) -> datetime:
        if isinstance(v, datetime):
            return v if v.tzinfo else v.replace(tzinfo=UTC)
        if isinstance(v, str):
            parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        raise ValueError("snapshot_timestamp required")


class BenchmarkCatalogFile(BaseModel):
    """Корень JSON-файла каталога."""

    items: list[BenchmarkProductRecord]


@dataclass
class BenchmarkBundleRecord:
    """ORM-готовые объекты для upsert в БД."""

    product: BenchmarkProductDB
    reviews: list[BenchmarkReviewDB]
    external: ExternalSummarySnapshotDB | None


def _to_orm_bundle(rec: BenchmarkProductRecord) -> BenchmarkBundleRecord:
    pid = rec.id or uuid4()
    product = BenchmarkProductDB(
        id=pid,
        benchmark_set_name=rec.benchmark_set_name,
        platform_name=rec.platform_name,
        product_external_id=rec.product_external_id,
        product_title=rec.product_title,
        product_url=rec.product_url,
        snapshot_timestamp=rec.snapshot_timestamp,
        category=rec.category,
        notes=rec.notes,
    )
    reviews: list[BenchmarkReviewDB] = []
    for rv in rec.reviews:
        rid = rv.id or uuid4()
        reviews.append(
            BenchmarkReviewDB(
                id=rid,
                benchmark_product_id=pid,
                review_external_id=rv.review_external_id,
                rating=rv.rating,
                title=rv.title,
                plus=rv.plus,
                minus=rv.minus,
                comment=rv.comment,
                review_date=rv.review_date,
                source_url=rv.source_url,
            )
        )
    external: ExternalSummarySnapshotDB | None = None
    if rec.external_summary is not None:
        ext = rec.external_summary
        external = ExternalSummarySnapshotDB(
            id=uuid4(),
            benchmark_product_id=pid,
            platform_name=rec.platform_name,
            summary_text=ext.summary_text,
            pros_text=ext.pros_text,
            cons_text=ext.cons_text,
            highlights_json=ext.highlights,
            raw_block_json=ext.raw_block,
            snapshot_timestamp=rec.snapshot_timestamp,
        )
    return BenchmarkBundleRecord(product=product, reviews=reviews, external=external)


def parse_benchmark_catalog_json(raw: str, *, label: str = "json") -> list[BenchmarkBundleRecord]:
    """Парсит тело каталога (сырая строка JSON) в список bundle для записи в БД."""
    data = json.loads(raw)
    if isinstance(data, list):
        catalog = BenchmarkCatalogFile.model_validate({"items": data})
    else:
        catalog = BenchmarkCatalogFile.model_validate(data)
    out: list[BenchmarkBundleRecord] = []
    for item in catalog.items:
        out.append(_to_orm_bundle(item))
    logger.info("Разобрано {} benchmark товаров из {}", len(out), label)
    return out


def load_benchmark_catalog_from_json(path: Path | str) -> list[BenchmarkBundleRecord]:
    """Читает JSON каталога и возвращает список bundle для записи в БД."""
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    return parse_benchmark_catalog_json(raw, label=str(p))


def export_snapshot_jsonl(bundles: list[BenchmarkBundleRecord], path: Path | str) -> None:
    """Экспорт frozen snapshot в JSONL (одна строка JSON на товар)."""
    p = Path(path)
    lines: list[str] = []
    for b in bundles:
        payload = {
            "benchmark_product": {
                "id": str(b.product.id),
                "benchmark_set_name": b.product.benchmark_set_name,
                "platform_name": b.product.platform_name,
                "product_external_id": b.product.product_external_id,
                "product_title": b.product.product_title,
                "product_url": b.product.product_url,
                "snapshot_timestamp": b.product.snapshot_timestamp.isoformat(),
                "category": b.product.category,
                "notes": b.product.notes,
            },
            "reviews": [
                {
                    "id": str(r.id),
                    "review_external_id": r.review_external_id,
                    "rating": r.rating,
                    "title": r.title,
                    "plus": r.plus,
                    "minus": r.minus,
                    "comment": r.comment,
                    "review_date": r.review_date.isoformat() if r.review_date else None,
                    "source_url": r.source_url,
                }
                for r in b.reviews
            ],
            "external_summary": None
            if b.external is None
            else {
                "summary_text": b.external.summary_text,
                "pros_text": b.external.pros_text,
                "cons_text": b.external.cons_text,
                "highlights_json": b.external.highlights_json,
                "raw_block_json": b.external.raw_block_json,
                "snapshot_timestamp": b.external.snapshot_timestamp.isoformat(),
            },
        }
        lines.append(json.dumps(payload, ensure_ascii=False))
    p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    logger.info("Экспорт JSONL: {} строк в {}", len(lines), p)


def load_benchmark_catalog_from_yaml(path: Path | str) -> list[BenchmarkBundleRecord]:
    """Опционально: YAML каталог (если установлен PyYAML)."""
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("Для YAML установите пакет PyYAML") from exc
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, list):
        catalog = BenchmarkCatalogFile.model_validate({"items": raw})
    else:
        catalog = BenchmarkCatalogFile.model_validate(raw)
    return [_to_orm_bundle(item) for item in catalog.items]
