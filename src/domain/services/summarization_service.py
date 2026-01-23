from typing import List, Dict, Any, TYPE_CHECKING

from src.domain.models.review import Review
from src.domain.models.summary import Summary

if TYPE_CHECKING:
    from src.infrastructure.services.summarization.base import BaseSummarizationMethod


class SummarizationService:
    def __init__(self, methods: Dict[str, "BaseSummarizationMethod"]) -> None:
        self._methods = methods

    def get_available_methods(self) -> List[str]:
        """Возвращает список доступных методов суммаризации."""
        return list(self._methods.keys())

    def get_method(self, method_code: str) -> "BaseSummarizationMethod":
        """Возвращает метод суммаризации по коду."""
        if method_code not in self._methods:
            raise ValueError(f"Метод '{method_code}' не найден. Доступные методы: {self.get_available_methods()}")
        return self._methods[method_code]

    async def summarize(
        self,
        product_id: str,
        reviews: List[Review],
        method_code: str,
        params: Dict[str, Any] | None = None,
    ) -> Summary:
        """Выполняет суммаризацию отзывов выбранным методом."""
        method = self.get_method(method_code)
        params = params or {}
        
        return await method.summarize(
            product_id=product_id,
            reviews=reviews,
            params=params,
        )
