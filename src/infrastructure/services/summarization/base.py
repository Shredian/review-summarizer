from abc import ABC, abstractmethod
from typing import List, Dict, Any

from src.domain.models.review import Review
from src.domain.models.summary import Summary


class BaseSummarizationMethod(ABC):
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
        reviews: List[Review],
        params: Dict[str, Any],
    ) -> Summary:
        """Выполняет суммаризацию отзывов."""
        pass

    async def persist_artifacts(self, summary: Summary) -> None:
        """Опциональный пост-процессинг после сохранения Summary в БД."""
        return None

    def get_info(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "version": self.version,
            "description": self.description,
        }
