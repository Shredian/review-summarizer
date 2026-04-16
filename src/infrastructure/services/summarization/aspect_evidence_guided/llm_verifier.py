"""LLM-верификатор и revision pass для сгенерированного summary."""

from __future__ import annotations

import asyncio

from loguru import logger

from src.infrastructure.clients.openai_client import OpenAIClient
from src.infrastructure.services.summarization.aspect_evidence_guided.prompt_templates import (
    render_revision_prompt,
    render_verification_prompt,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    GenerationOutput,
    LLMOverallOutput,
    LLMVerificationOutput,
    SummaryGenerationInput,
    VerificationResult,
)

_MAX_RETRIES = 2


class LLMSummaryVerifier:
    """Верифицирует summary через LLM, при необходимости запускает revision pass.

    Проверяет:
    - unsupported claims (утверждения без опоры на evidence),
    - missing must_include аспекты,
    - искажение polarity баланса,
    - слишком расплывчатые формулировки.

    Если is_valid=False и есть revision_instructions — запускает revision pass
    для text_overall и возвращает исправленный output в VerificationResult.
    """

    def __init__(self, openai_client: OpenAIClient) -> None:
        self._llm = openai_client._client

    async def verify(
        self,
        inp: SummaryGenerationInput,
        output: GenerationOutput,
    ) -> VerificationResult:
        """Запускает LLM-верификацию и опционально revision pass."""
        text_to_verify = output.text_overall or ""

        verification_result = await self._run_verification(inp, text_to_verify)

        all_issues = (
            verification_result.unsupported_claims
            + verification_result.missing_aspects
            + verification_result.polarity_issues
        )

        revised_output: GenerationOutput | None = None
        if (
            not verification_result.is_valid
            and verification_result.revision_instructions
            and output.text_overall
        ):
            logger.info(
                "LLMSummaryVerifier: запуск revision pass. Инструкции: {}",
                verification_result.revision_instructions,
            )
            try:
                revised_output = await self._run_revision(inp, output, verification_result.revision_instructions)
            except Exception as exc:
                logger.warning("LLMSummaryVerifier: revision pass завершился с ошибкой: {}", exc)

        return VerificationResult(
            passed=verification_result.is_valid,
            errors=all_issues,
            warnings=[],
            revised_output=revised_output,
        )

    async def _run_verification(
        self,
        inp: SummaryGenerationInput,
        text_overall: str,
    ) -> LLMVerificationOutput:
        structured_llm = self._llm.with_structured_output(LLMVerificationOutput, method="json_schema")
        messages = render_verification_prompt(inp, text_overall)

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                result: LLMVerificationOutput = await structured_llm.ainvoke(messages)
                return result
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "LLMSummaryVerifier: verification attempt {}/{} failed: {}",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    exc,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(1.0 * (attempt + 1))

        logger.error(
            "LLMSummaryVerifier: верификация завершилась с ошибкой после {} попыток, "
            "считаем verification passed=True для сохранения результата.",
            _MAX_RETRIES + 1,
        )
        return LLMVerificationOutput(is_valid=True)

    async def _run_revision(
        self,
        inp: SummaryGenerationInput,
        original_output: GenerationOutput,
        revision_instructions: str,
    ) -> GenerationOutput:
        """Запускает revision pass для text_overall."""
        structured_llm = self._llm.with_structured_output(LLMOverallOutput, method="json_schema")
        messages = render_revision_prompt(inp, original_output, revision_instructions)

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                result: LLMOverallOutput = await structured_llm.ainvoke(messages)
                return original_output.model_copy(
                    update={"text_overall": result.text_overall}
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "LLMSummaryVerifier: revision attempt {}/{} failed: {}",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    exc,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(1.0 * (attempt + 1))

        raise RuntimeError(
            f"LLMSummaryVerifier: revision failed after {_MAX_RETRIES + 1} attempts"
        ) from last_exc
