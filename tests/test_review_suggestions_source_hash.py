from uuid import uuid4

from src.domain.models.review import Review
from src.domain.review_suggestions.source_hash import compute_product_source_hash


def test_product_source_hash_stable_and_changes_with_text() -> None:
    pid = uuid4()
    rid = uuid4()
    base = Review(
        id=rid,
        product_id=pid,
        user_id=None,
        source="wb",
        comment="норм",
    )
    h1 = compute_product_source_hash(pid, [base])
    h2 = compute_product_source_hash(pid, [base.model_copy(update={"comment": "отлично"})])
    assert h1 != h2


def test_product_source_hash_same_for_reorder() -> None:
    pid = uuid4()
    r1 = Review(
        id=uuid4(),
        product_id=pid,
        user_id=None,
        source="wb",
        comment="а",
    )
    r2 = Review(
        id=uuid4(),
        product_id=pid,
        user_id=None,
        source="wb",
        comment="б",
    )
    h_ab = compute_product_source_hash(pid, [r1, r2])
    h_ba = compute_product_source_hash(pid, [r2, r1])
    assert h_ab == h_ba
