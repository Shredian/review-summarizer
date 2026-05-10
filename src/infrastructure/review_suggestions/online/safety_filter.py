from __future__ import annotations

import re

from src.domain.review_suggestions.entities import SuggestionCandidate, TextInputState

_BAD = re.compile(
    r"(полгода|3\s*месяц|неделю|достав|за\s*\d+\s*дн|руб|₽|\d{4}-\d{2}|"
    r"сломался|через\s*неделю|лучший\s*товар|на\s*рынке)",
    re.I,
)
_DATE = re.compile(r"\d{1,2}\.\d{1,2}\.\d{2,4}")


class SuggestionSafetyFilter:
    """Отсекает кандидатов подсказок с рискованным или нерелевантным содержимым."""

    def filter(
        self, candidates: list[SuggestionCandidate], state: TextInputState
    ) -> list[SuggestionCandidate]:
        ctx_low = state.text_before_cursor.lower()
        out: list[SuggestionCandidate] = []
        for c in candidates:
            t = c.insert_text or c.text
            if len(t) > 80:
                continue
            if _BAD.search(t):
                continue
            if _DATE.search(t):
                continue
            low = t.lower().strip()
            if low and low in ctx_low:
                continue
            # сроки использования, если пользователь сам не начал
            if any(
                x in low for x in ("месяц", "неделю", "полгода", "недели", "дней", "дня")
            ) and not any(
                x in ctx_low for x in ("месяц", "неделю", "полгод", "недел", "дней", "дня")
            ):
                continue
            out.append(c)
        return out
