from abc import ABC, abstractmethod
from typing import Any

from src.domain.models.review import Review
from src.domain.models.summary import Summary


class BaseSummarizationMethod(ABC):
    """Базовый контракт метода суммаризации (код, версия, summarize, опционально артефакты в БД)."""

    @property
    @abstractmethod
    def code(self) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @property
    def description(self) -> str:
        return ""

    @abstractmethod
    async def summarize(
        self,
        product_id: str,
        reviews: list[Review],
        params: dict[str, Any],
    ) -> Summary:
        pass

    async def persist_artifacts(self, summary: Summary) -> None:
        return None

    def get_info(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "version": self.version,
            "description": self.description,
        }
