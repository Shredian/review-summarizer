from __future__ import annotations

import re

from src.domain.review_suggestions.entities import TextInputState

_NON_WORD = re.compile(r"[^\w\-]+", re.UNICODE)


def build_text_input_state(
    current_text: str,
    cursor_position: int,
    *,
    field: str,
    rating: float | None,
) -> TextInputState:
    cur = max(0, min(cursor_position, len(current_text)))
    before = current_text[:cur]
    raw = current_text
    is_empty = len(before.strip()) == 0
    ends_space = len(before) > 0 and before[-1].isspace()
    # последнее «слово» до курсора (без пробелов)
    token_m = list(re.finditer(r"[\w\-]+", before, flags=re.UNICODE))
    current_token = token_m[-1].group(0).lower() if token_m else None
    rough_tokens = [t.group(0).lower() for t in re.finditer(r"[\w\-]+", before, flags=re.UNICODE)]
    last_surface = rough_tokens[-8:] if rough_tokens else []
    last_lemmas = last_surface  # без pymorphy в online — lemmas ≈ surface
    return TextInputState(
        raw_text=raw,
        text_before_cursor=before,
        current_token=current_token,
        last_surface_tokens=last_surface,
        last_lemmas=last_lemmas,
        is_empty=is_empty,
        ends_with_space=ends_space,
        field=field,
        rating=rating,
    )
