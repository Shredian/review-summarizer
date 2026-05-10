import unittest
from uuid import uuid4

from src.domain.models.review import Review
from src.infrastructure.services.summarization.aspect_evidence_guided.aggregator import (
    EvidenceAggregator,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.evidence_selector import (
    EvidenceSelector,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.grounded_generator import (
    GroundedGenerator,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.normalizer import (
    ReviewNormalizer,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.planner import ContentPlanner
from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    AspectEvidenceGuidedParams,
    CanonicalAspect,
    MentionExtractionResult,
    SectionType,
    SentimentLabel,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.scorer import AspectScorer
from src.infrastructure.services.summarization.aspect_evidence_guided.verifier import (
    SummaryVerifier,
)


class TestAspectEvidencePipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.review = Review(
            id=uuid4(),
            product_id=uuid4(),
            user_id=None,
            source="ozon",
            url=None,
            rating=5.0,
            title="Отличная батарея",
            comment="Заряд держит долго и экран яркий.",
            plus="Долго работает",
            minus="Нет",
        )

    def test_normalizer_adds_section_markers(self) -> None:
        normalizer = ReviewNormalizer()
        items = normalizer.normalize([self.review])
        self.assertEqual(len(items), 1)
        self.assertIn("[TITLE]", items[0].canonical_text)
        self.assertIn("[PLUS]", items[0].canonical_text)

    def test_planner_and_verifier_pipeline(self) -> None:
        mentions = [
            MentionExtractionResult(
                review_id=self.review.id,
                section_type=SectionType.COMMENT,
                span_text="Заряд держит долго.",
                aspect_raw="батарея",
                aspect_candidate="батарея",
                sentiment_label=SentimentLabel.POSITIVE,
                sentiment_score=0.9,
                extractor_confidence=0.8,
            ),
            MentionExtractionResult(
                review_id=self.review.id,
                section_type=SectionType.COMMENT,
                span_text="Экран яркий.",
                aspect_raw="экран",
                aspect_candidate="экран",
                sentiment_label=SentimentLabel.POSITIVE,
                sentiment_score=0.7,
                extractor_confidence=0.8,
            ),
        ]
        canonical = [
            CanonicalAspect(canonical_name="батарея", aliases=["батарея"], mentions=[mentions[0]]),
            CanonicalAspect(canonical_name="экран", aliases=["экран"], mentions=[mentions[1]]),
        ]

        aggregated = EvidenceAggregator().aggregate(canonical, reviews_count=1)
        scored = AspectScorer().score(aggregated, AspectEvidenceGuidedParams())
        plan = ContentPlanner().build_plan(scored, AspectEvidenceGuidedParams())
        evidence = EvidenceSelector().select(plan, canonical, evidence_per_aspect=2)
        output = GroundedGenerator().generate(plan, evidence)
        verification = SummaryVerifier().verify(plan, evidence, output)

        self.assertGreaterEqual(len(plan.selected_aspects), 2)
        self.assertTrue(verification.passed)
        self.assertTrue(output.text_overall)


if __name__ == "__main__":
    unittest.main()
