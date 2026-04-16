"""LLM-генератор summary на основе aspect-evidence структур."""

from __future__ import annotations

import asyncio
from typing import TypeVar

from loguru import logger

from src.infrastructure.clients.openai_client import OpenAIClient
from src.infrastructure.services.summarization.aspect_evidence_guided.prompt_templates import (
    render_cons_prompt,
    render_overall_prompt,
    render_pros_prompt,
)
from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    GenerationOutput,
    LLMConsOutput,
    LLMOverallOutput,
    LLMProsOutput,
    SummaryGenerationInput,
)

_T = TypeVar("_T")

_MAX_RETRIES = 2


class LLMGroundedGenerator:
    """Генерирует summary через LLM, опираясь на aspect-level aggregated data.

    Три секции (overall, pros, cons) генерируются параллельно через
    LangChain with_structured_output. При исчерпании попыток возвращает None
    для соответствующей секции — orchestrator должен обработать это
    или сделать fallback на GroundedGenerator.
    """

    def __init__(self, openai_client: OpenAIClient) -> None:
        self._llm = openai_client._client

    async def generate(self, inp: SummaryGenerationInput) -> GenerationOutput:
        """Параллельно генерирует overall, pros и cons."""
        overall_task = asyncio.create_task(self._generate_overall(inp))
        pros_task = asyncio.create_task(self._generate_pros(inp))
        cons_task = asyncio.create_task(self._generate_cons(inp))

        overall, pros, cons = await asyncio.gather(
            overall_task, pros_task, cons_task, return_exceptions=True
        )

        text_overall = overall if isinstance(overall, str) else None
        text_pros = pros if isinstance(pros, str) else None
        text_cons = cons if isinstance(cons, str) else None

        if isinstance(overall, Exception):
            logger.warning("LLMGroundedGenerator: overall generation failed: {}", overall)
        if isinstance(pros, Exception):
            logger.warning("LLMGroundedGenerator: pros generation failed: {}", pros)
        if isinstance(cons, Exception):
            logger.warning("LLMGroundedGenerator: cons generation failed: {}", cons)

        if text_overall is None and text_pros is None and text_cons is None:
            raise RuntimeError("LLMGroundedGenerator: все три секции завершились с ошибкой")

        return GenerationOutput(
            text_overall=text_overall,
            text_pros=text_pros,
            text_cons=text_cons,
            text_neutral=None,
            key_phrases=[],
        )

    async def _generate_overall(self, inp: SummaryGenerationInput) -> str:
        messages = render_overall_prompt(
            inp,
            max_sentences=inp.generation_constraints.max_sentences,
        )
        result: LLMOverallOutput = await self._call_with_retry(
            messages=messages,
            output_schema=LLMOverallOutput,
            label="overall",
        )
        return result.text_overall

    async def _generate_pros(self, inp: SummaryGenerationInput) -> str:
        messages = render_pros_prompt(inp)
        result: LLMProsOutput = await self._call_with_retry(
            messages=messages,
            output_schema=LLMProsOutput,
            label="pros",
        )
        return result.text_pros

    async def _generate_cons(self, inp: SummaryGenerationInput) -> str:
        messages = render_cons_prompt(inp)
        result: LLMConsOutput = await self._call_with_retry(
            messages=messages,
            output_schema=LLMConsOutput,
            label="cons",
        )
        return result.text_cons

    async def _call_with_retry(
        self,
        messages: list,
        output_schema: type[_T],
        label: str,
    ) -> _T:
        """Вызывает LLM с structured output. Повторяет до _MAX_RETRIES раз."""
        structured_llm = self._llm.with_structured_output(output_schema, method="json_schema")
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                result = await structured_llm.ainvoke(messages)
                return result
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "LLMGroundedGenerator [{}] attempt {}/{} failed: {}",
                    label,
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    exc,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(1.0 * (attempt + 1))

        raise RuntimeError(
            f"LLMGroundedGenerator [{label}] failed after {_MAX_RETRIES + 1} attempts"
        ) from last_exc
