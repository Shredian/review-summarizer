"""Тесты для LLMSummaryVerifier."""

import unittest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.infrastructure.services.summarization.aspect_evidence_guided.llm_verifier import (
    LLMSummaryVerifier,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    AspectSummaryInput,
    EvidenceInput,
    GenerationConstraints,
    GenerationOutput,
    LLMOverallOutput,
    LLMVerificationOutput,
    SectionType,
    SentimentLabel,
    SummaryGenerationInput,
    VerificationResult,
)


def _make_generation_input() -> SummaryGenerationInput:
    evidence = EvidenceInput(
        text="Батарея держит долго",
        section_type=SectionType.PLUS,
        sentiment_label=SentimentLabel.POSITIVE,
        evidence_score=0.85,
    )
    aspect = AspectSummaryInput(
        aspect_name="батарея",
        importance_score=0.75,
        prevalence_score=0.5,
        total_mentions=8,
        positive_mentions=7,
        negative_mentions=1,
        neutral_mentions=0,
        target_polarity="positive",
        rarity_flag=False,
        must_include=False,
        aliases=[],
        representative_evidence=[evidence],
    )
    return SummaryGenerationInput(
        product_id=uuid4(),
        reviews_count=15,
        rating_avg=4.1,
        selected_aspects=[aspect],
        generation_constraints=GenerationConstraints(),
    )


def _make_output(text_overall: str = "Хороший продукт.") -> GenerationOutput:
    return GenerationOutput(
        text_overall=text_overall,
        text_pros="Хорошая батарея.",
        text_cons=None,
        text_neutral=None,
        key_phrases=[],
    )


def _make_mock_client_for_verification(
    verification: LLMVerificationOutput,
    revision_text: str | None = None,
) -> MagicMock:
    mock_llm = MagicMock()

    def structured_output_side_effect(schema, **kwargs):
        runnable = AsyncMock()
        if schema is LLMVerificationOutput:
            runnable.ainvoke = AsyncMock(return_value=verification)
        elif schema is LLMOverallOutput:
            text = revision_text or "Исправленный summary."
            runnable.ainvoke = AsyncMock(return_value=LLMOverallOutput(text_overall=text))
        return runnable

    mock_llm.with_structured_output = MagicMock(side_effect=structured_output_side_effect)
    openai_mock = MagicMock()
    openai_mock._client = mock_llm
    return openai_mock


class TestLLMSummaryVerifier(unittest.IsolatedAsyncioTestCase):
    async def test_valid_output_returns_passed_true(self) -> None:
        verification_response = LLMVerificationOutput(
            is_valid=True,
            unsupported_claims=[],
            missing_aspects=[],
            polarity_issues=[],
            revision_instructions=None,
        )
        client = _make_mock_client_for_verification(verification_response)
        verifier = LLMSummaryVerifier(client)

        result = await verifier.verify(_make_generation_input(), _make_output())

        self.assertIsInstance(result, VerificationResult)
        self.assertTrue(result.passed)
        self.assertEqual(result.errors, [])
        self.assertIsNone(result.revised_output)

    async def test_invalid_output_triggers_revision_pass(self) -> None:
        verification_response = LLMVerificationOutput(
            is_valid=False,
            unsupported_claims=["Придуманный факт"],
            missing_aspects=[],
            polarity_issues=[],
            revision_instructions="Убери неподтверждённые факты.",
        )
        client = _make_mock_client_for_verification(
            verification_response,
            revision_text="Исправленный вариант без выдуманных фактов.",
        )
        verifier = LLMSummaryVerifier(client)

        result = await verifier.verify(_make_generation_input(), _make_output())

        self.assertFalse(result.passed)
        self.assertIn("Придуманный факт", result.errors)
        self.assertIsNotNone(result.revised_output)
        self.assertEqual(
            result.revised_output.text_overall,
            "Исправленный вариант без выдуманных фактов.",
        )

    async def test_invalid_without_instructions_no_revision(self) -> None:
        verification_response = LLMVerificationOutput(
            is_valid=False,
            unsupported_claims=["Что-то лишнее"],
            missing_aspects=[],
            polarity_issues=[],
            revision_instructions=None,
        )
        client = _make_mock_client_for_verification(verification_response)
        verifier = LLMSummaryVerifier(client)

        result = await verifier.verify(_make_generation_input(), _make_output())

        self.assertFalse(result.passed)
        self.assertIsNone(result.revised_output)

    async def test_verification_llm_failure_returns_passed_true(self) -> None:
        """При падении LLM верификации считаем passed=True (сохраняем результат)."""
        mock_llm = MagicMock()

        def failing_structured_output(schema, **kwargs):
            runnable = AsyncMock()
            runnable.ainvoke = AsyncMock(side_effect=RuntimeError("API unavailable"))
            return runnable

        mock_llm.with_structured_output = MagicMock(side_effect=failing_structured_output)
        openai_mock = MagicMock()
        openai_mock._client = mock_llm

        verifier = LLMSummaryVerifier(openai_mock)
        result = await verifier.verify(_make_generation_input(), _make_output())

        self.assertTrue(result.passed)
        self.assertIsNone(result.revised_output)

    async def test_multiple_error_types_aggregated(self) -> None:
        verification_response = LLMVerificationOutput(
            is_valid=False,
            unsupported_claims=["claim1"],
            missing_aspects=["aspect1"],
            polarity_issues=["polarity_issue1"],
            revision_instructions="Исправить всё.",
        )
        client = _make_mock_client_for_verification(verification_response)
        verifier = LLMSummaryVerifier(client)

        result = await verifier.verify(_make_generation_input(), _make_output())

        self.assertFalse(result.passed)
        self.assertIn("claim1", result.errors)
        self.assertIn("aspect1", result.errors)
        self.assertIn("polarity_issue1", result.errors)


if __name__ == "__main__":
    unittest.main()
