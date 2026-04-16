"""Prompt templates для LLM-генерации summary на основе aspect-evidence структур."""

from __future__ import annotations

import json

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    AspectSummaryInput,
    GenerationOutput,
    SummaryGenerationInput,
)

# ---------------------------------------------------------------------------
# Вспомогательный рендерер аспектов
# ---------------------------------------------------------------------------

_MAX_EVIDENCE_PER_ASPECT = 3
_MAX_ASPECTS_IN_PROMPT = 8


def _render_aspects_block(
    aspects: list[AspectSummaryInput],
    max_aspects: int = _MAX_ASPECTS_IN_PROMPT,
    max_evidence: int = _MAX_EVIDENCE_PER_ASPECT,
) -> str:
    """Рендерит список аспектов в компактный JSON-блок для вставки в промпт."""
    selected = aspects[:max_aspects]
    items = []
    for asp in selected:
        evidence = [
            {"text": ev.text, "sentiment": ev.sentiment_label.value}
            for ev in asp.representative_evidence[:max_evidence]
        ]
        items.append(
            {
                "aspect_name": asp.aspect_name,
                "importance_score": round(asp.importance_score, 3),
                "prevalence_score": round(asp.prevalence_score, 3),
                "mentions": {
                    "positive": asp.positive_mentions,
                    "negative": asp.negative_mentions,
                    "neutral": asp.neutral_mentions,
                    "total": asp.total_mentions,
                },
                "target_polarity": asp.target_polarity,
                "must_include": asp.must_include,
                "representative_evidence": evidence,
            }
        )
    return json.dumps(items, ensure_ascii=False, indent=2)


def _render_positive_aspects_block(
    aspects: list[AspectSummaryInput],
    max_evidence: int = _MAX_EVIDENCE_PER_ASPECT,
) -> str:
    """Рендерит только аспекты с положительной поддержкой."""
    positive = [
        a for a in aspects if a.positive_mentions > 0 and a.target_polarity in ("positive", "balanced")
    ]
    return _render_aspects_block(positive, max_evidence=max_evidence)


def _render_negative_aspects_block(
    aspects: list[AspectSummaryInput],
    max_evidence: int = _MAX_EVIDENCE_PER_ASPECT,
) -> str:
    """Рендерит только аспекты с отрицательной поддержкой."""
    negative = [
        a for a in aspects if a.negative_mentions > 0 and a.target_polarity in ("negative", "balanced")
    ]
    return _render_aspects_block(negative, max_evidence=max_evidence)


# ---------------------------------------------------------------------------
# render_overall_prompt
# ---------------------------------------------------------------------------

_OVERALL_SYSTEM = """\
Ты — AI-копирайтер, специализирующийся на составлении емких обзоров товаров на основе анализа пользовательских мнений.
Твоя задача — по переданным агрегированным аспектам и фрагментам evidence создать один связный итоговый текст.
Используй только переданные аспекты, статистику и подтверждающие фрагменты; не придумывай новые аспекты, свойства и выводы.
Не делай рекламных утверждений.
Если аспект встречается редко — формулируй это осторожно: "некоторые пользователи отмечают".
Если по аспекту есть противоречивые мнения — отрази это явно и нейтрально.
Отвечай строго в JSON-формате: {"text_overall": "..."}.\
"""


def render_overall_prompt(
    inp: SummaryGenerationInput,
    max_sentences: int | None = None,
) -> list[BaseMessage]:
    """Промпт для генерации text_overall."""
    sentences = max_sentences or inp.generation_constraints.max_sentences
    aspects_block = _render_aspects_block(inp.selected_aspects)

    user_content = f"""\
Даны следующие данные:
1. Общие сведения об отзывах о {inp.generation_constraints.category}:
   - количество отзывов: {inp.reviews_count}
   - средний рейтинг: {inp.rating_avg if inp.rating_avg is not None else "не указан"}

2. Агрегированные аспекты и подтверждающие фрагменты (JSON):
{aspects_block}

**Твоя задача**:
Составить одно связное **обобщение мнений пользователей** о {inp.generation_constraints.category}. Текст должен полно отражать суть и опираться только на входные данные.

**Основные требования**:
1.  **Отсутствие первого лица**: Избегай формулировок "я", "мне", "мой" и т.п. Вместо этого используй обороты вроде "пользователи отмечают", "некоторые жалуются", "в целом товар характеризуется" и т.п.
2.  **Опора на переданные данные**: Обязательно опирайся на аспекты и фразы из representative_evidence; формулировки из evidence включай органично и **корректно склоняй** в соответствии с грамматическим контекстом.
3.  **Выделение фраз тегами**: Для явно положительных и отрицательных формулировок из evidence используй теги `<span class="positive">...</span>` и `<span class="negative">...</span>`, как в примере ниже.
4.  **Избегание повторений**: Старайся не повторять одни и те же преимущества или недостатки в рамках текста, если это возможно без потери смысла. Ищи синонимичные или более общие формулировки, если одна и та же мысль уже выражена.
5.  **Дополнение контекста фраз**: Если фразы из evidence кажутся вырванными из контекста или слишком короткими для органичной вставки, ты можешь **дополнить их минимально необходимым контекстом**, чтобы они звучали естественно в предложении. Главное — сохранить исходный смысл и эмоциональную окраску.

**Дополнительные ограничения (метод аспектной генерации)**:
- Длина: не более {sentences} предложений; один связный абзац без маркированных списков.
- Не используй сведения, которых нет во входных данных.
- Сначала упоминай наиболее важные аспекты (выше importance_score).
- Не пиши шаблонные фразы вроде "товар отличный" или "идеальный выбор".
- Аспекты с must_include=true обязательно должны быть упомянуты.
- Для аспектов с высоким prevalence_score допустимо "часто упоминают"; для низкого — только "некоторые пользователи отмечают".
- Если по аспекту есть смешанные мнения — покажи это аккуратно.

**Структура обобщения**:
*   **Нейтральное обобщение**: Представь как положительные, так и отрицательные аспекты, отмеченные пользователями. Текст может начинаться с фразы "Пользователи отмечают", и большая часть текста должна описывать сильные стороны, но также кратко упоминай и слабые стороны, если они есть во входных данных.

**Пример оформления (стиль должен быть похожим, но текст — лаконичнее)**:
> "Пользователи отмечают, что товар обладает достоинствами, такими как <span class="positive">преимущество 1</span> и <span class="positive">преимущество 2</span>. Тем не менее, некоторые обращают внимание на <span class="negative">недостаток 1</span>, что стоит учесть."

Сформируй, пожалуйста, итоговое обобщение согласно указанным требованиям.
Ответ должен быть в формате JSON, например:

{{"text_overall": "..."}}\
"""
    return [SystemMessage(content=_OVERALL_SYSTEM), HumanMessage(content=user_content)]


# ---------------------------------------------------------------------------
# render_pros_prompt
# ---------------------------------------------------------------------------

_PROS_SYSTEM = """\
Ты формируешь краткое описание преимуществ продукта по пользовательским отзывам.
Используй только аспекты с подтверждённой положительной полярностью.
Не включай аспекты с недостаточной поддержкой (малым числом positive_mentions).
Не делай рекламных формулировок.
Отвечай строго в JSON-формате: {"text_pros": "..."}.\
"""


def render_pros_prompt(inp: SummaryGenerationInput) -> list[BaseMessage]:
    """Промпт для генерации text_pros."""
    aspects_block = _render_positive_aspects_block(inp.selected_aspects)

    if not aspects_block or aspects_block == "[]":
        aspects_block = _render_aspects_block(inp.selected_aspects)

    user_content = f"""\
Ниже переданы аспекты, для которых есть положительные пользовательские оценки \
(категория: {inp.generation_constraints.category}, отзывов: {inp.reviews_count}).

Аспекты с положительной поддержкой (JSON):
{aspects_block}

Требования:
1. Напиши краткий связный текст о преимуществах продукта на русском языке.
2. Упоминай только реально поддержанные положительные аспекты \
(ориентируйся на positive_mentions > 0).
3. Не добавляй рекламные формулировки.
4. Не повторяй одинаковые мысли разными словами.
5. Не используй списки — только связный текст.
6. Если положительных аспектов мало — напиши об этом честно и кратко.

Верни JSON:
{{"text_pros": "..."}}\
"""
    return [SystemMessage(content=_PROS_SYSTEM), HumanMessage(content=user_content)]


# ---------------------------------------------------------------------------
# render_cons_prompt
# ---------------------------------------------------------------------------

_CONS_SYSTEM = """\
Ты формируешь краткое описание недостатков продукта по пользовательским отзывам.
Используй только аспекты с подтверждённой отрицательной полярностью.
Не драматизируй и не усиливай негатив сверх переданных evidence.
Не придумывай новые проблемы.
Отвечай строго в JSON-формате: {"text_cons": "..."}.\
"""


def render_cons_prompt(inp: SummaryGenerationInput) -> list[BaseMessage]:
    """Промпт для генерации text_cons."""
    aspects_block = _render_negative_aspects_block(inp.selected_aspects)

    if not aspects_block or aspects_block == "[]":
        aspects_block = _render_aspects_block(inp.selected_aspects)

    user_content = f"""\
Ниже переданы аспекты, для которых есть отрицательные пользовательские оценки \
(категория: {inp.generation_constraints.category}, отзывов: {inp.reviews_count}).

Аспекты с отрицательной поддержкой (JSON):
{aspects_block}

Требования:
1. Напиши краткий связный текст о недостатках продукта на русском языке.
2. Не придумывай новые проблемы.
3. Если негатив по аспекту не доминирующий (negative_mentions меньше positive_mentions) — \
формулируй осторожно: "часть пользователей отмечает".
4. Не используй списки — только связный текст.
5. Если явных недостатков мало — напиши об этом честно и кратко.

Верни JSON:
{{"text_cons": "..."}}\
"""
    return [SystemMessage(content=_CONS_SYSTEM), HumanMessage(content=user_content)]


# ---------------------------------------------------------------------------
# render_verification_prompt
# ---------------------------------------------------------------------------

_VERIFICATION_SYSTEM = """\
Ты проверяешь summary на соответствие входным аспектам и evidence.
Нужно выявить: unsupported claims, пропущенные обязательные аспекты, \
искажение полярности, слишком общие / расплывчатые фразы.
Отвечай строго в JSON-формате согласно схеме.\
"""


def render_verification_prompt(
    inp: SummaryGenerationInput,
    text_overall: str,
) -> list[BaseMessage]:
    """Промпт для верификации сгенерированного summary."""
    aspects_block = _render_aspects_block(inp.selected_aspects)
    must_include = [a.aspect_name for a in inp.selected_aspects if a.must_include]

    user_content = f"""\
Входные аспекты и evidence:
{aspects_block}

Обязательные аспекты (must_include=true): {must_include if must_include else "нет"}

Сгенерированный summary:
"{text_overall}"

Проверь:
1. Есть ли утверждения, не подтверждённые evidence (unsupported_claims).
2. Все ли аспекты с must_include=true явно отражены (missing_aspects).
3. Нет ли неправильной передачи positive/negative баланса (polarity_issues).
4. Если есть проблемы — сформулируй краткие инструкции по правке (revision_instructions).

Верни JSON:
{{
  "is_valid": true/false,
  "unsupported_claims": [],
  "missing_aspects": [],
  "polarity_issues": [],
  "revision_instructions": "..." или null
}}\
"""
    return [SystemMessage(content=_VERIFICATION_SYSTEM), HumanMessage(content=user_content)]


# ---------------------------------------------------------------------------
# render_revision_prompt
# ---------------------------------------------------------------------------

_REVISION_SYSTEM = """\
Ты исправляешь summary по инструкциям верификатора.
Используй только переданные аспекты и evidence.
Не добавляй новую информацию, не указанную во входных данных.
Отвечай строго в JSON-формате: {"text_overall": "..."}.\
"""


def render_revision_prompt(
    inp: SummaryGenerationInput,
    original_output: GenerationOutput,
    revision_instructions: str,
) -> list[BaseMessage]:
    """Промпт для revision pass после неуспешной верификации."""
    aspects_block = _render_aspects_block(inp.selected_aspects)

    user_content = f"""\
Исходный summary, который нужно исправить:
"{original_output.text_overall}"

Инструкции по правке от верификатора:
{revision_instructions}

Входные аспекты и evidence:
{aspects_block}

Статистика: отзывов {inp.reviews_count}, \
средний рейтинг {inp.rating_avg if inp.rating_avg is not None else "не указан"}.

Напиши исправленный summary на русском языке. \
Устрани все указанные проблемы. Не вноси изменений, кроме необходимых.

Верни JSON:
{{"text_overall": "..."}}\
"""
    return [SystemMessage(content=_REVISION_SYSTEM), HumanMessage(content=user_content)]
