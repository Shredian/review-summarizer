"""Загрузка продуктов с числом отзывов и подписи для selectbox в Streamlit."""

from __future__ import annotations

from collections import Counter

from src.container import Container
from src.domain.models.product import Product


async def load_products_with_review_counts(
    *,
    limit: int = 1000,
    offset: int = 0,
) -> list[tuple[Product, int]]:
    app = Container.product_application()
    return await app.list_with_reviews_count(limit=limit, offset=offset)


def format_product_option_label(product: Product, reviews_count: int) -> str:
    return f"{product.name} ({reviews_count} отз.)"


def build_product_choice_map(items: list[tuple[Product, int]]) -> dict[str, Product]:
    """Подпись → продукт. При одинаковых имени и числе отзывов добавляется суффикс id."""
    base_totals = Counter(format_product_option_label(p, c) for p, c in items)
    per_base_order: Counter[str] = Counter()
    out: dict[str, Product] = {}
    for product, cnt in items:
        base = format_product_option_label(product, cnt)
        per_base_order[base] += 1
        if base_totals[base] > 1:
            pid = str(product.id)[:8] if product.id else str(per_base_order[base])
            label = f"{base} [{pid}]"
        else:
            label = base
        candidate = label
        dup = 1
        while candidate in out:
            dup += 1
            candidate = f"{label} ({dup})"
        out[candidate] = product
    return out
