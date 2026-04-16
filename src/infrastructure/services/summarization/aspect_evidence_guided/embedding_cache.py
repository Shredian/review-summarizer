"""Общий кэш SentenceTransformer по имени модели (один экземпляр на процесс)."""

from __future__ import annotations

from threading import Lock
from typing import Any

_cache: dict[str, Any] = {}
_lock = Lock()


def get_shared_sentence_transformer(model_name: str) -> Any | None:
    """Возвращает кэшированный SentenceTransformer или None, если пакет недоступен."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:  # pragma: no cover
        return None
    with _lock:
        if model_name not in _cache:
            _cache[model_name] = SentenceTransformer(model_name)
        return _cache[model_name]
