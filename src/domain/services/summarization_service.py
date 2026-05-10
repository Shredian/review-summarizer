from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.domain.models.review import Review
from src.domain.models.summary import Summary

if TYPE_CHECKING:
    from src.infrastructure.services.summarization.base import BaseSummarizationMethod


class SummarizationService:
    """Выбор зарегистрированного метода суммаризации и вызов summarize."""

    def __init__(self, methods: dict[str, BaseSummarizationMethod]) -> None:
        self._methods = methods

    def get_available_methods(self) -> list[str]:
        return list(self._methods.keys())

    def get_method(self, method_code: str) -> BaseSummarizationMethod:
        if method_code not in self._methods:
            raise ValueError(
                f"Метод '{method_code}' не найден. Доступные методы: {self.get_available_methods()}"
            )
        return self._methods[method_code]

    async def summarize(
        self,
        product_id: str,
        reviews: list[Review],
        method_code: str,
        params: dict[str, Any] | None = None,
    ) -> Summary:
        method = self.get_method(method_code)
        params = params or {}

        return await method.summarize(
            product_id=product_id,
            reviews=reviews,
            params=params,
        )
