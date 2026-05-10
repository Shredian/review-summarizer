"""Тесты для _build_generation_input в AspectEvidenceGuidedSummarizationMethod."""

import unittest
from uuid import uuid4

from src.domain.models.review import Review
from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    AspectEvidenceGuidedParams,
    AspectStats,
    ContentPlan,
    EvidenceItem,
    PlannedAspect,
    SectionType,
    SentimentLabel,
)
from src.infrastructure.services.summarization.aspect_evidence_guided_method import (
    AspectEvidenceGuidedSummarizationMethod,
)


class _FakeRepo:
    async def create_many(self, values):
        return []

    async def create(self, value):
        return value.id


def _make_method() -> AspectEvidenceGuidedSummarizationMethod:
    return AspectEvidenceGuidedSummarizationMethod(
        aspect_mention_repository=_FakeRepo(),
        aspect_cluster_repository=_FakeRepo(),
        summary_evidence_repository=_FakeRepo(),
        summary_plan_repository=_FakeRepo(),
        openai_client=None,
    )


def _make_review(rating: float = 4.5) -> Review:
    return Review(
        id=uuid4(),
        product_id=uuid4(),
        user_id=None,
        source="test",
        url=None,
        rating=rating,
        title="Хороший товар",
        comment="Качество на высоте",
        plus="Удобно",
        minus="",
        review_date=None,
    )


def _make_aspect_stats(name: str, pos: int = 3, neg: int = 1) -> AspectStats:
    return AspectStats(
        aspect_name=name,
        aliases=[f"{name}_alias"],
        total_mentions=pos + neg,
        positive_mentions=pos,
        negative_mentions=neg,
        neutral_mentions=0,
        mixed_mentions=0,
        source_count=1,
        review_count=pos + neg,
        section_distribution={"plus": pos, "minus": neg},
        prevalence_score=round((pos + neg) / 10.0, 3),
        importance_score=0.75,
    )


def _make_plan(aspect_names: list[str]) -> ContentPlan:
    return ContentPlan(
        selected_aspects=[
            PlannedAspect(
                aspect_name=name,
                target_polarity="positive",
                importance_score=0.8,
                rarity_flag=False,
                expected_mentions=4,
            )
            for name in aspect_names
        ],
        dropped_aspects=[],
        diagnostics={},
    )


def _make_evidence_items(aspect_names: list[str]) -> list[EvidenceItem]:
    items = []
    for name in aspect_names:
        items.append(
            EvidenceItem(
                review_id=uuid4(),
                aspect_name=name,
                section_type=SectionType.PLUS,
                evidence_text=f"Хорошо: {name}",
                polarity=SentimentLabel.POSITIVE,
                rank=1,
            )
        )
        items.append(
            EvidenceItem(
                review_id=uuid4(),
                aspect_name=name,
                section_type=SectionType.MINUS,
                evidence_text=f"Плохо: {name}",
                polarity=SentimentLabel.NEGATIVE,
                rank=2,
            )
        )
    return items


class TestBuildGenerationInput(unittest.TestCase):
    def setUp(self) -> None:
        self.method = _make_method()
        self.product_id = str(uuid4())
        self.params = AspectEvidenceGuidedParams()
        self.aspect_names = ["качество", "цена", "доставка"]

    def test_basic_structure(self) -> None:
        reviews = [_make_review(4.0), _make_review(5.0)]
        plan = _make_plan(self.aspect_names)
        evidence = _make_evidence_items(self.aspect_names)
        scored = [_make_aspect_stats(n) for n in self.aspect_names]

        result = self.method._build_generation_input(
            plan=plan,
            evidence_items=evidence,
            scored_aspects=scored,
            reviews=reviews,
            product_id=self.product_id,
            params=self.params,
        )

        self.assertEqual(result.reviews_count, 2)
        self.assertAlmostEqual(result.rating_avg, 4.5, places=1)
        self.assertEqual(len(result.selected_aspects), len(self.aspect_names))

    def test_aspect_fields_mapped_correctly(self) -> None:
        reviews = [_make_review()]
        plan = _make_plan(["качество"])
        evidence = _make_evidence_items(["качество"])
        scored = [_make_aspect_stats("качество", pos=5, neg=2)]

        result = self.method._build_generation_input(
            plan=plan,
            evidence_items=evidence,
            scored_aspects=scored,
            reviews=reviews,
            product_id=self.product_id,
            params=self.params,
        )

        asp = result.selected_aspects[0]
        self.assertEqual(asp.aspect_name, "качество")
        self.assertEqual(asp.positive_mentions, 5)
        self.assertEqual(asp.negative_mentions, 2)
        self.assertEqual(asp.total_mentions, 7)
        self.assertIn("качество_alias", asp.aliases)

    def test_evidence_per_aspect_capped(self) -> None:
        params = AspectEvidenceGuidedParams(evidence_per_aspect=1)
        reviews = [_make_review()]
        plan = _make_plan(["цена"])
        evidence = _make_evidence_items(["цена"])
        scored = [_make_aspect_stats("цена")]

        result = self.method._build_generation_input(
            plan=plan,
            evidence_items=evidence,
            scored_aspects=scored,
            reviews=reviews,
            product_id=self.product_id,
            params=params,
        )

        asp = result.selected_aspects[0]
        self.assertLessEqual(len(asp.representative_evidence), 1)

    def test_no_ratings_returns_none_avg(self) -> None:
        reviews = [
            Review(
                id=uuid4(),
                product_id=uuid4(),
                user_id=None,
                source="test",
                url=None,
                rating=None,
                title="",
                comment="текст",
                plus=None,
                minus=None,
                review_date=None,
            )
        ]
        plan = _make_plan(["дизайн"])
        evidence = _make_evidence_items(["дизайн"])
        scored = [_make_aspect_stats("дизайн")]

        result = self.method._build_generation_input(
            plan=plan,
            evidence_items=evidence,
            scored_aspects=scored,
            reviews=reviews,
            product_id=self.product_id,
            params=self.params,
        )

        self.assertIsNone(result.rating_avg)

    def test_generation_constraints_from_params(self) -> None:
        params = AspectEvidenceGuidedParams(category="ноутбук", llm_overall_sentences=7)
        reviews = [_make_review()]
        plan = _make_plan(["экран"])
        evidence = _make_evidence_items(["экран"])
        scored = [_make_aspect_stats("экран")]

        result = self.method._build_generation_input(
            plan=plan,
            evidence_items=evidence,
            scored_aspects=scored,
            reviews=reviews,
            product_id=self.product_id,
            params=params,
        )

        self.assertEqual(result.generation_constraints.category, "ноутбук")
        self.assertEqual(result.generation_constraints.max_sentences, 7)

    def test_rarity_flag_sets_must_include(self) -> None:
        reviews = [_make_review()]
        plan = ContentPlan(
            selected_aspects=[
                PlannedAspect(
                    aspect_name="редкий_аспект",
                    target_polarity="negative",
                    importance_score=0.3,
                    rarity_flag=True,
                    expected_mentions=1,
                )
            ],
            dropped_aspects=[],
            diagnostics={},
        )
        evidence = _make_evidence_items(["редкий_аспект"])
        scored = [_make_aspect_stats("редкий_аспект")]

        result = self.method._build_generation_input(
            plan=plan,
            evidence_items=evidence,
            scored_aspects=scored,
            reviews=reviews,
            product_id=self.product_id,
            params=self.params,
        )

        self.assertTrue(result.selected_aspects[0].must_include)


if __name__ == "__main__":
    unittest.main()
