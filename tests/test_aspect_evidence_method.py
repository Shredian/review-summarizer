import unittest
from uuid import uuid4

from src.domain.models.review import Review
from src.infrastructure.services.summarization.aspect_evidence_guided_method import (
    AspectEvidenceGuidedSummarizationMethod,
)


class _FakeCreateManyRepository:
    def __init__(self) -> None:
        self.items = []

    async def create_many(self, values):
        self.items.extend(values)
        return [item.id for item in values]


class _FakeCreateRepository:
    def __init__(self) -> None:
        self.items = []

    async def create(self, value):
        self.items.append(value)
        return value.id


class TestAspectEvidenceMethod(unittest.IsolatedAsyncioTestCase):
    async def test_method_generates_summary_and_artifacts(self) -> None:
        mention_repo = _FakeCreateManyRepository()
        cluster_repo = _FakeCreateManyRepository()
        evidence_repo = _FakeCreateManyRepository()
        plan_repo = _FakeCreateRepository()
        method = AspectEvidenceGuidedSummarizationMethod(
            aspect_mention_repository=mention_repo,
            aspect_cluster_repository=cluster_repo,
            summary_evidence_repository=evidence_repo,
            summary_plan_repository=plan_repo,
        )
        product_id = uuid4()
        reviews = [
            Review(
                id=uuid4(),
                product_id=product_id,
                user_id=None,
                source="wb",
                url=None,
                rating=5.0,
                title="Качественная сборка",
                comment="Батарея работает долго, но цена высокая.",
                plus="Хороший экран",
                minus="Дороговато",
            ),
            Review(
                id=uuid4(),
                product_id=product_id,
                user_id=None,
                source="ozon",
                url=None,
                rating=3.0,
                title="Нормально",
                comment="Доставка быстрая, но корпус маркий.",
                plus="Быстрая доставка",
                minus="Маркий корпус",
            ),
        ]

        summary = await method.summarize(
            product_id=str(product_id),
            reviews=reviews,
            params={"max_selected_aspects": 6, "min_selected_aspects": 3},
        )

        self.assertEqual(summary.method, "aspect_evidence_guided_v1")
        self.assertIsNotNone(summary.id)
        self.assertTrue(summary.params.get("diagnostics"))
        self.assertEqual(len(mention_repo.items), 0)
        self.assertEqual(len(cluster_repo.items), 0)
        self.assertEqual(len(plan_repo.items), 0)

        await method.persist_artifacts(summary)
        self.assertGreater(len(mention_repo.items), 0)
        self.assertGreater(len(cluster_repo.items), 0)
        self.assertEqual(len(plan_repo.items), 1)


if __name__ == "__main__":
    unittest.main()
