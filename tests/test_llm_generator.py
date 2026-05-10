"""Тесты для LLMGroundedGenerator."""

import unittest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.infrastructure.services.summarization.aspect_evidence_guided.llm_generator import (
    LLMGroundedGenerator,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    AspectSummaryInput,
    EvidenceInput,
    GenerationConstraints,
    GenerationOutput,
    LLMConsOutput,
    LLMOverallOutput,
    LLMProsOutput,
    SectionType,
    SentimentLabel,
    SummaryGenerationInput,
)


def _make_generation_input() -> SummaryGenerationInput:
    evidence = EvidenceInput(
        text="Качество хорошее",
        section_type=SectionType.PLUS,
        sentiment_label=SentimentLabel.POSITIVE,
        evidence_score=0.9,
    )
    aspect = AspectSummaryInput(
        aspect_name="качество",
        importance_score=0.8,
        prevalence_score=0.6,
        total_mentions=10,
        positive_mentions=8,
        negative_mentions=2,
        neutral_mentions=0,
        target_polarity="positive",
        rarity_flag=False,
        must_include=False,
        aliases=["качество материала"],
        representative_evidence=[evidence],
    )
    return SummaryGenerationInput(
        product_id=uuid4(),
        reviews_count=20,
        rating_avg=4.3,
        selected_aspects=[aspect],
        generation_constraints=GenerationConstraints(
            category="товар",
            max_sentences=5,
        ),
    )


def _make_mock_client(overall_text: str, pros_text: str, cons_text: str) -> MagicMock:
    """Создаёт мок OpenAIClient с настроенным with_structured_output."""
    mock_client = MagicMock()

    def structured_output_side_effect(schema, **kwargs):
        runnable = AsyncMock()
        if schema is LLMOverallOutput:
            runnable.ainvoke = AsyncMock(return_value=LLMOverallOutput(text_overall=overall_text))
        elif schema is LLMProsOutput:
            runnable.ainvoke = AsyncMock(return_value=LLMProsOutput(text_pros=pros_text))
        elif schema is LLMConsOutput:
            runnable.ainvoke = AsyncMock(return_value=LLMConsOutput(text_cons=cons_text))
        return runnable

    mock_client.with_structured_output = MagicMock(side_effect=structured_output_side_effect)

    openai_mock = MagicMock()
    openai_mock._client = mock_client
    return openai_mock


class TestLLMGroundedGenerator(unittest.IsolatedAsyncioTestCase):
    async def test_generate_returns_generation_output(self) -> None:
        client = _make_mock_client("Общий summary.", "Плюсы продукта.", "Минусы продукта.")
        generator = LLMGroundedGenerator(client)
        inp = _make_generation_input()

        result = await generator.generate(inp)

        self.assertIsInstance(result, GenerationOutput)
        self.assertEqual(result.text_overall, "Общий summary.")
        self.assertEqual(result.text_pros, "Плюсы продукта.")
        self.assertEqual(result.text_cons, "Минусы продукта.")

    async def test_generate_partial_failure_returns_none_sections(self) -> None:
        """Если одна секция падает — остальные сохраняются, None для упавшей."""
        mock_client = MagicMock()

        call_count = {"n": 0}

        def structured_output_side_effect(schema, **kwargs):
            runnable = AsyncMock()
            call_count["n"] += 1
            if schema is LLMOverallOutput:
                runnable.ainvoke = AsyncMock(return_value=LLMOverallOutput(text_overall="Общий."))
            elif schema is LLMProsOutput:
                runnable.ainvoke = AsyncMock(side_effect=RuntimeError("LLM error"))
            elif schema is LLMConsOutput:
                runnable.ainvoke = AsyncMock(return_value=LLMConsOutput(text_cons="Минусы."))
            return runnable

        mock_client.with_structured_output = MagicMock(side_effect=structured_output_side_effect)
        openai_mock = MagicMock()
        openai_mock._client = mock_client

        generator = LLMGroundedGenerator(openai_mock)
        inp = _make_generation_input()

        result = await generator.generate(inp)

        self.assertEqual(result.text_overall, "Общий.")
        self.assertIsNone(result.text_pros)
        self.assertEqual(result.text_cons, "Минусы.")

    async def test_generate_all_fail_raises_runtime_error(self) -> None:
        """Если все три секции падают — должен бросить RuntimeError."""
        mock_client = MagicMock()

        def failing_structured_output(schema, **kwargs):
            runnable = AsyncMock()
            runnable.ainvoke = AsyncMock(side_effect=RuntimeError("API error"))
            return runnable

        mock_client.with_structured_output = MagicMock(side_effect=failing_structured_output)
        openai_mock = MagicMock()
        openai_mock._client = mock_client

        generator = LLMGroundedGenerator.__new__(LLMGroundedGenerator)
        generator._llm = mock_client

        inp = _make_generation_input()
        with self.assertRaises(RuntimeError):
            await generator.generate(inp)

    async def test_retry_on_transient_failure(self) -> None:
        """Генератор делает повторную попытку после одиночной ошибки."""
        mock_llm = MagicMock()
        attempt = {"n": 0}

        def structured_output_side_effect(schema, **kwargs):
            runnable = AsyncMock()

            async def ainvoke_with_retry(messages):
                attempt["n"] += 1
                if schema is LLMOverallOutput and attempt["n"] == 1:
                    raise RuntimeError("Transient error")
                if schema is LLMOverallOutput:
                    return LLMOverallOutput(text_overall="Retry success.")
                if schema is LLMProsOutput:
                    return LLMProsOutput(text_pros="Pros.")
                return LLMConsOutput(text_cons="Cons.")

            runnable.ainvoke = ainvoke_with_retry
            return runnable

        mock_llm.with_structured_output = MagicMock(side_effect=structured_output_side_effect)

        generator = LLMGroundedGenerator.__new__(LLMGroundedGenerator)
        generator._llm = mock_llm

        inp = _make_generation_input()
        result = await generator.generate(inp)

        self.assertEqual(result.text_overall, "Retry success.")


if __name__ == "__main__":
    unittest.main()
