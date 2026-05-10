from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

from src.infrastructure.clients.openai_client import OpenAIClient

from src.utils.logger import logger


def parse_json_object_from_llm(text: str) -> dict[str, Any]:
    """Извлекает JSON из ответа LLM (в т.ч. с markdown fences)."""
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```\s*$", "", raw)
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            return json.loads(m.group())
        raise


class JudgeRubricOutput(BaseModel):
    faithfulness_score: float | None = Field(default=None)
    coverage_score: float | None = Field(default=None)
    sentiment_consistency_score: float | None = Field(default=None)
    specificity_score: float | None = Field(default=None)
    overall_preference: float | None = Field(default=None, description="0-10 полезность")
    rationale: str | None = None
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_aspects: list[str] = Field(default_factory=list)


class JudgePairwiseOutput(BaseModel):
    faithfulness_score: float | None = None
    coverage_score: float | None = None
    sentiment_consistency_score: float | None = None
    specificity_score: float | None = None
    overall_preference: float | None = None
    winner: str | None = Field(default=None, description="A | B | tie")
    rationale: str | None = None
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_aspects: list[str] = Field(default_factory=list)


def build_compact_ledger_prompt_block(aspect_lines: list[str]) -> str:
    lines = []
    for block in aspect_lines:
        lines.append(block)
    return "\n".join(lines)


class EvaluationLLMJudge:
    """Rubric и pairwise сравнение на компактном structured input."""

    def __init__(self, client: OpenAIClient | None) -> None:
        self._client = client

    async def score_rubric(
        self,
        *,
        candidate_summary: str,
        aspect_reference_lines: list[str],
        product_title: str,
    ) -> JudgeRubricOutput | None:
        if self._client is None:
            return None
        prompt = f"""Ты оценщик качества summary отзывов о товаре.
Товар: {product_title}

Reference (аспекты и доказательства; НЕ подставляй новые факты, сверяй фактичность по ним):
{build_compact_ledger_prompt_block(aspect_reference_lines)}

Candidate summary:
{candidate_summary}

Оцени по шкале 0..10 (числа с плавающей точкой допустимы): faithfulness, coverage, sentiment_consistency, specificity, overall_preference.
Верни JSON с ключами:
faithfulness_score, coverage_score, sentiment_consistency_score, specificity_score, overall_preference,
rationale (кратко), unsupported_claims (массив строк), missing_aspects (массив строк).
Только JSON."""
        try:
            raw = await self._client.send_request(prompt, temperature=0.2)
            data = parse_json_object_from_llm(raw)
            return JudgeRubricOutput.model_validate(data)
        except Exception as exc:
            logger.warning("LLM rubric judge failed: {}", exc)
            return None

    async def compare_pairwise(
        self,
        *,
        summary_a: str,
        summary_b: str,
        label_a: str,
        label_b: str,
        aspect_reference_lines: list[str],
        product_title: str,
    ) -> JudgePairwiseOutput | None:
        if self._client is None:
            return None
        ref = build_compact_ledger_prompt_block(aspect_reference_lines)
        prompt = f"""Товар: {product_title}
Reference (аспекты и доказательства):
{ref}

Сравни два summary. {label_a} = вариант A, {label_b} = вариант B.

A:
{summary_a}

B:
{summary_b}

Оцени 0..10: faithfulness, coverage, sentiment_consistency, specificity для каждого варианта в среднем (overall_preference — какой полезнее пользователю).
winner: строка ровно одна из: "A", "B", "tie".
Верни JSON с ключами faithfulness_score, coverage_score, sentiment_consistency_score, specificity_score, overall_preference, winner, rationale, unsupported_claims, missing_aspects.
Только JSON."""
        try:
            raw = await self._client.send_request(prompt, temperature=0.2)
            data = parse_json_object_from_llm(raw)
            return JudgePairwiseOutput.model_validate(data)
        except Exception as exc:
            logger.warning("LLM pairwise judge failed: {}", exc)
            return None

    async def pairwise_with_swap(
        self,
        *,
        our_summary: str,
        external_summary: str,
        aspect_reference_lines: list[str],
        product_title: str,
    ) -> dict[str, Any]:
        """Два прогона с перестановкой A/B для снижения position bias."""
        first = await self.compare_pairwise(
            summary_a=our_summary,
            summary_b=external_summary,
            label_a="our_method",
            label_b="external_platform",
            aspect_reference_lines=aspect_reference_lines,
            product_title=product_title,
        )
        second = await self.compare_pairwise(
            summary_a=external_summary,
            summary_b=our_summary,
            label_a="external_platform",
            label_b="our_method",
            aspect_reference_lines=aspect_reference_lines,
            product_title=product_title,
        )
        out: dict[str, Any] = {"run1": first.model_dump() if first else None, "run2": second.model_dump() if second else None}
        # Агрегация winner: map A/B к our/external
        def map_winner(o: JudgePairwiseOutput | None, ours_is_a: bool) -> str | None:
            if o is None or not o.winner:
                return None
            w = o.winner.upper()
            if w == "TIE":
                return "tie"
            if w == "A":
                return "our_method" if ours_is_a else "external_platform"
            if w == "B":
                return "external_platform" if ours_is_a else "our_method"
            return None

        w1 = map_winner(first, ours_is_a=True)
        w2 = map_winner(second, ours_is_a=False)
        votes = [x for x in (w1, w2) if x]
        if not votes:
            agg = None
        elif votes.count("our_method") > votes.count("external_platform"):
            agg = "our_method"
        elif votes.count("external_platform") > votes.count("our_method"):
            agg = "external_platform"
        else:
            agg = "tie"
        out["aggregate_winner"] = agg
        return out
