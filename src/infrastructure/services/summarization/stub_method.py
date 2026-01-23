from datetime import datetime
from typing import List, Dict, Any
from uuid import UUID

from src.domain.models.review import Review
from src.domain.models.summary import Summary, KeyPhraseItem
from src.infrastructure.services.summarization.base import BaseSummarizationMethod


class StubSummarizationMethod(BaseSummarizationMethod):
    """Заглушка метода суммаризации для тестирования.
    
    Возвращает тестовые данные без реальной суммаризации.
    """

    @property
    def code(self) -> str:
        return "stub"

    @property
    def name(self) -> str:
        return "Тестовый метод (заглушка)"

    @property
    def version(self) -> str:
        return "v0.1.0"

    @property
    def description(self) -> str:
        return "Метод-заглушка для тестирования. Возвращает предопределённые тестовые данные."

    async def summarize(
        self,
        product_id: str,
        reviews: List[Review],
        params: Dict[str, Any],
    ) -> Summary:
        """Возвращает тестовый результат суммаризации."""
        
        # Вычисляем статистику по отзывам
        reviews_count = len(reviews)
        
        ratings = [r.rating for r in reviews if r.rating is not None]
        rating_avg = sum(ratings) / len(ratings) if ratings else None
        
        dates = [r.review_date for r in reviews if r.review_date is not None]
        date_min = min(dates) if dates else None
        date_max = max(dates) if dates else None
        
        # Формируем тестовый результат
        # В реальном методе здесь была бы логика суммаризации
        
        text_overall = None
        text_neutral = None
        text_pros = None
        text_cons = None
        key_phrases = None
        
        # Определяем тип результата по параметрам
        output_type = params.get("output_type", "structured")
        
        if output_type == "overall":
            text_overall = self._generate_overall_text(reviews)
        else:
            text_neutral = self._generate_neutral_text(reviews)
            text_pros = self._generate_pros_text(reviews)
            text_cons = self._generate_cons_text(reviews)
            key_phrases = self._generate_key_phrases(reviews)
        
        return Summary(
            product_id=UUID(product_id) if isinstance(product_id, str) else product_id,
            method=self.code,
            method_version=self.version,
            params=params,
            created_at=datetime.now(),
            reviews_count=reviews_count,
            rating_avg=rating_avg,
            date_min=date_min,
            date_max=date_max,
            text_overall=text_overall,
            text_neutral=text_neutral,
            text_pros=text_pros,
            text_cons=text_cons,
            key_phrases=key_phrases,
        )

    def _generate_overall_text(self, reviews: List[Review]) -> str:
        """Генерирует общий текст суммаризации (заглушка)."""
        return (
            f"Это тестовая суммаризация {len(reviews)} отзывов. "
            "В реальном методе здесь будет результат работы алгоритма суммаризации."
        )

    def _generate_neutral_text(self, reviews: List[Review]) -> str:
        """Генерирует нейтральное резюме (заглушка)."""
        return (
            f"Проанализировано {len(reviews)} отзывов. "
            "Пользователи отмечают как положительные, так и отрицательные стороны продукта."
        )

    def _generate_pros_text(self, reviews: List[Review]) -> str:
        """Генерирует текст о плюсах (заглушка)."""
        # Собираем реальные плюсы из отзывов, если есть
        pros_list = [r.plus for r in reviews if r.plus]
        if pros_list:
            return f"Основные плюсы по мнению пользователей: {'; '.join(pros_list[:3])}..."
        return "Пользователи отмечают качество продукта и соотношение цена/качество."

    def _generate_cons_text(self, reviews: List[Review]) -> str:
        """Генерирует текст о минусах (заглушка)."""
        # Собираем реальные минусы из отзывов, если есть
        cons_list = [r.minus for r in reviews if r.minus]
        if cons_list:
            return f"Основные минусы по мнению пользователей: {'; '.join(cons_list[:3])}..."
        return "Некоторые пользователи отмечают отдельные недостатки, требующие внимания."

    def _generate_key_phrases(self, reviews: List[Review]) -> List[KeyPhraseItem]:
        """Генерирует ключевые фразы (заглушка)."""
        # Тестовые ключевые фразы
        return [
            KeyPhraseItem(
                phrase="хорошее качество",
                sentiment="positive",
                count=5,
                share=0.25,
            ),
            KeyPhraseItem(
                phrase="быстрая доставка",
                sentiment="positive",
                count=3,
                share=0.15,
            ),
            KeyPhraseItem(
                phrase="соответствует описанию",
                sentiment="neutral",
                count=4,
                share=0.20,
            ),
            KeyPhraseItem(
                phrase="мелкие недочёты",
                sentiment="negative",
                count=2,
                share=0.10,
            ),
        ]
