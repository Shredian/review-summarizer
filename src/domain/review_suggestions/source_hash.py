from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import UUID

from src.domain.models.review import Review


def _dt_key(d: datetime | None) -> str:
    if d is None:
        return ""
    if d.tzinfo is not None:
        return d.isoformat()
    return d.replace(tzinfo=None).isoformat()


def _review_content_hash(r: Review) -> str:
    payload = {
        "title": r.title or "",
        "comment": r.comment or "",
        "plus": r.plus or "",
        "minus": r.minus or "",
        "rating": r.rating,
        "review_date": _dt_key(r.review_date),
        "created_at": _dt_key(r.created_at),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_product_reviews_fingerprint_rows(reviews: list[Review]) -> str:
    rows: list[tuple[str, str, str]] = []
    for r in reviews:
        rows.append((str(r.id), str(r.product_id), _review_content_hash(r)))
    rows.sort(key=lambda x: x[0])
    canonical = json.dumps(rows, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_user_reviews_fingerprint_rows(reviews: list[Review]) -> str:
    rows: list[tuple[str, str, str]] = []
    for r in reviews:
        rows.append((str(r.id), str(r.product_id), _review_content_hash(r)))
    rows.sort(key=lambda x: x[0])
    canonical = json.dumps(rows, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_product_source_hash(product_id: UUID, reviews: list[Review]) -> str:
    inner = compute_product_reviews_fingerprint_rows(reviews)
    raw = f"{product_id}:{inner}".encode()
    return hashlib.sha256(raw).hexdigest()


def compute_user_source_hash(user_id: UUID, reviews: list[Review]) -> str:
    inner = compute_user_reviews_fingerprint_rows(reviews)
    raw = f"{user_id}:{inner}".encode()
    return hashlib.sha256(raw).hexdigest()
