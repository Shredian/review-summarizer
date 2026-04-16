"""Метод аспектной суммаризации отзывов с O(1) затратами токенов по количеству отзывов."""

import json
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from src.domain.models.review import Review
from src.domain.models.summary import Summary, KeyPhraseItem
from src.infrastructure.clients.openai_client import OpenAIClient
from src.infrastructure.services.summarization.base import BaseSummarizationMethod
from src.infrastructure.services.summarization.config import get_user_reference
from src.infrastructure.services.summarization.preprocessing import (
    lemmatize_text,
    get_review_sentences_with_context,
)
from src.infrastructure.services.summarization.prompts import (
    EXTRACT_ASPECTS_PROMPT,
    GENERATE_REVIEWS_PROMPT,
    GENERATE_REVIEWS_PROMPT_SOFT,
    CORRECTION_PROMPT,
)
from src.utils.logger import logger


@dataclass
class PhraseData:
    """Данные о фразе из отзывов (для аспектного метода)."""

    phrase: str
    lemmatized: str
    sentiment: str  # 'positive' или 'negative'
    count: int = 0


class AspectSummarizationMethod(BaseSummarizationMethod):
    """Метод аспектной суммаризации с O(1) затратами токенов по N отзывов.

    Pipeline:
    1. Стратифицированная выборка 30-50 отзывов
    2. LLM: извлечение 5-8 аспектов + ключевые слова
    3. Локальный поиск фраз по всем отзывам
    4. Генерация обобщённых отзывов через LLM
    5. Корректура грамматики через LLM
    """

    def __init__(
        self,
        openai_client: OpenAIClient,
        openai_client_mini: OpenAIClient,
    ) -> None:
        self._openai_client = openai_client
        self._openai_client_mini = openai_client_mini

    @property
    def code(self) -> str:
        return "aspect"

    @property
    def name(self) -> str:
        return "Аспектная суммаризация"

    @property
    def version(self) -> str:
        return "v1.0.0"

    @property
    def description(self) -> str:
        return (
            "Метод с O(1) затратами токенов по количеству отзывов. "
            "Извлекает аспекты по выборке, ищет фразы локально по всем отзывам, "
            "генерирует обобщённые отзывы (положительный, отрицательный, нейтральный)."
        )

    async def summarize(
        self,
        product_id: str,
        reviews: List[Review],
        params: Dict[str, Any],
    ) -> Summary:
        """Выполняет суммаризацию отзывов."""
        category = params.get("category", "товар")
        use_soft_mode = params.get("use_soft_mode", False)
        sample_size = params.get("sample_size", 50)
        aspects_count = params.get("aspects_count", 8)
        phrases_per_aspect = params.get("phrases_per_aspect", 5)
        representative_count = params.get("representative_count", 10)

        logger.info(f"Начало аспектной суммаризации для продукта {product_id}")
        logger.info(
            f"Параметры: category={category}, sample_size={sample_size}, reviews_count={len(reviews)}"
        )

        reviews_with_text = [r for r in reviews if r.get_full_text()]
        if not reviews_with_text:
            logger.warning("Нет текстов отзывов для анализа")
            raise ValueError("Нет текстов отзывов для анализа")

        # 1. Стратифицированная выборка
        sample_reviews = self._sample_reviews(reviews_with_text, sample_size)
        sample_texts = [r.get_full_text() for r in sample_reviews]
        reviews_sample = "\n---\n".join(
            f"[{i+1}] {text}" for i, text in enumerate(sample_texts)
        )

        logger.info(f"Выборка: {len(sample_reviews)} отзывов")

        # 2. Извлечение аспектов через LLM
        aspects_dict = await self._extract_aspects(reviews_sample, category)
        if not aspects_dict:
            logger.warning("Не удалось извлечь аспекты")
            return self._create_empty_summary(product_id, reviews, params)

        logger.info(f"Извлечено {len(aspects_dict)} аспектов: {list(aspects_dict.keys())}")

        # 3. Локальный поиск фраз по всем отзывам
        phrases_data = self._search_phrases_by_aspect(
            reviews_with_text, aspects_dict, phrases_per_aspect
        )

        if not phrases_data:
            logger.warning("Не удалось найти фразы по аспектам")
            return self._create_empty_summary(product_id, reviews, params)

        logger.info(f"Найдено {len(phrases_data)} фраз")

        # 4. Формирование key_phrases
        total_reviews = len(reviews_with_text)
        key_phrases = [
            KeyPhraseItem(
                phrase=p.phrase,
                sentiment=p.sentiment,
                count=p.count,
                share=round(p.count / total_reviews, 2) if total_reviews else 0,
            )
            for p in sorted(phrases_data, key=lambda x: x.count, reverse=True)[:30]
        ]

        # 5. Выбор репрезентативных отзывов
        all_texts = [r.get_full_text() for r in reviews_with_text]
        representative_reviews = self._select_representative_reviews(
            all_texts, representative_count
        )

        # 6. Генерация обобщённых отзывов
        generated_reviews = await self._generate_reviews(
            phrases_data, representative_reviews, category, use_soft_mode
        )

        # 7. Корректура
        if generated_reviews:
            generated_reviews = await self._correct_reviews(generated_reviews)

        # Статистика
        ratings = [r.rating for r in reviews if r.rating is not None]
        rating_avg = sum(ratings) / len(ratings) if ratings else None
        dates = [r.review_date for r in reviews if r.review_date is not None]
        date_min = min(dates) if dates else None
        date_max = max(dates) if dates else None

        return Summary(
            product_id=UUID(product_id) if isinstance(product_id, str) else product_id,
            method=self.code,
            method_version=self.version,
            params=params,
            created_at=datetime.now(),
            reviews_count=len(reviews),
            rating_avg=rating_avg,
            date_min=date_min,
            date_max=date_max,
            text_overall=None,
            text_neutral=generated_reviews.get("general") if generated_reviews else None,
            text_pros=generated_reviews.get("positive") if generated_reviews else None,
            text_cons=generated_reviews.get("negative") if generated_reviews else None,
            key_phrases=key_phrases if key_phrases else None,
        )

    def _sample_reviews(
        self, reviews: List[Review], sample_size: int
    ) -> List[Review]:
        """Стратифицированная выборка отзывов по рейтингу."""
        sample_size = min(sample_size, len(reviews))

        if len(reviews) <= sample_size or len(reviews) < 10:
            return random.sample(reviews, min(sample_size, len(reviews)))

        low = [r for r in reviews if r.rating is not None and r.rating <= 2]
        mid = [r for r in reviews if r.rating is not None and 2 < r.rating < 4]
        high = [r for r in reviews if r.rating is not None and r.rating >= 4]
        no_rating = [r for r in reviews if r.rating is None]

        total = len(reviews)
        n_low = max(1, round(sample_size * len(low) / total)) if low else 0
        n_mid = max(1, round(sample_size * len(mid) / total)) if mid else 0
        n_high = max(1, round(sample_size * len(high) / total)) if high else 0
        n_no = sample_size - n_low - n_mid - n_high
        if n_no < 0:
            n_no = 0

        result = []
        if low:
            result.extend(random.sample(low, min(n_low, len(low))))
        if mid:
            result.extend(random.sample(mid, min(n_mid, len(mid))))
        if high:
            result.extend(random.sample(high, min(n_high, len(high))))
        if no_rating and n_no > 0:
            result.extend(random.sample(no_rating, min(n_no, len(no_rating))))

        if len(result) < sample_size:
            remaining = [r for r in reviews if r not in result]
            result.extend(
                random.sample(remaining, min(sample_size - len(result), len(remaining)))
            )

        return result[:sample_size]

    async def _extract_aspects(
        self, reviews_sample: str, category: str
    ) -> Dict[str, List[str]]:
        """Извлекает аспекты и ключевые слова через LLM."""
        prompt = EXTRACT_ASPECTS_PROMPT.format(
            category=category, reviews_sample=reviews_sample
        )

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                response = await self._openai_client_mini.send_request(prompt)

                start = response.find("{")
                end = response.rfind("}") + 1
                if start == -1 or end == 0:
                    logger.warning(f"JSON не найден в ответе (попытка {attempt})")
                    continue

                aspects_dict = json.loads(response[start:end])

                if not isinstance(aspects_dict, dict):
                    logger.warning("Ответ не является словарём")
                    continue

                result = {}
                for k, v in aspects_dict.items():
                    if isinstance(v, list):
                        result[str(k)] = [str(x) for x in v if x]
                    elif isinstance(v, str):
                        result[str(k)] = [str(v)]

                if result:
                    return result

            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования JSON (попытка {attempt}): {e}")

        return {}

    def _search_phrases_by_aspect(
        self,
        reviews: List[Review],
        aspects_dict: Dict[str, List[str]],
        phrases_per_aspect: int,
    ) -> List[PhraseData]:
        """Локальный поиск фраз по аспектам во всех отзывах."""
        aspects_order = list(aspects_dict.keys())
        aspect_keywords: Dict[str, List[str]] = {}
        for aspect, keywords in aspects_dict.items():
            lemmas = [
                lemmatize_text(kw).strip()
                for kw in keywords
                if kw and lemmatize_text(kw).strip()
            ]
            if lemmas:
                aspect_keywords[aspect] = lemmas

        phrase_review_count: Dict[tuple, int] = defaultdict(int)
        phrase_to_aspects: Dict[tuple, set] = defaultdict(set)

        for review in reviews:
            review_phrases: set = set()
            for sentence, sentiment in get_review_sentences_with_context(review):
                if not sentence or len(sentence) < 5:
                    continue
                if sentiment not in ("positive", "negative"):
                    continue
                sent_normalized = " ".join(sentence.split())[:100]
                lem_sent = lemmatize_text(sentence)

                for aspect, keyword_lemmas in aspect_keywords.items():
                    for kw_lem in keyword_lemmas:
                        if kw_lem and kw_lem in lem_sent:
                            key = (sent_normalized, sentiment)
                            if key not in review_phrases:
                                review_phrases.add(key)
                                phrase_review_count[key] += 1
                            phrase_to_aspects[key].add(aspect)
                            break

        phrases_by_aspect: Dict[str, Dict[str, List[tuple]]] = {
            a: {"positive": [], "negative": []} for a in aspects_order
        }

        for (phrase, sentiment), count in phrase_review_count.items():
            for aspect in phrase_to_aspects.get((phrase, sentiment), []):
                if aspect in phrases_by_aspect:
                    phrases_by_aspect[aspect][sentiment].append((phrase, count))

        result: List[PhraseData] = []
        seen: set = set()

        for aspect in aspects_order:
            for sentiment in ("positive", "negative"):
                items = phrases_by_aspect[aspect][sentiment]
                items_sorted = sorted(items, key=lambda x: x[1], reverse=True)[
                    :phrases_per_aspect
                ]
                for phrase, count in items_sorted:
                    if (phrase, sentiment) not in seen:
                        seen.add((phrase, sentiment))
                        result.append(
                            PhraseData(
                                phrase=phrase,
                                lemmatized=lemmatize_text(phrase),
                                sentiment=sentiment,
                                count=count,
                            )
                        )

        return result

    def _select_representative_reviews(
        self, review_texts: List[str], count: int = 10
    ) -> List[str]:
        """Выбирает репрезентативные отзывы (самые длинные)."""
        sorted_reviews = sorted(review_texts, key=len, reverse=True)
        top_20 = sorted_reviews[:20]
        if len(top_20) > count:
            return random.sample(top_20, count)
        return top_20

    async def _generate_reviews(
        self,
        phrases: List[PhraseData],
        representative_reviews: List[str],
        category: str,
        use_soft_mode: bool,
    ) -> Optional[Dict[str, str]]:
        """Генерирует обобщённые отзывы через LLM."""
        positive_phrases = [p.phrase for p in phrases if p.sentiment == "positive"]
        negative_phrases = [p.phrase for p in phrases if p.sentiment == "negative"]

        if not positive_phrases and not negative_phrases:
            return None

        representative_reviews = self._format_representative_reviews(
            representative_reviews
        )

        user_reference = get_user_reference(category)
        user_reference_capitalized = user_reference.capitalize()

        prompt_template = (
            GENERATE_REVIEWS_PROMPT_SOFT if use_soft_mode else GENERATE_REVIEWS_PROMPT
        )
        prompt = prompt_template.format(
            category=category,
            representative_reviews=representative_reviews,
            positive_phrases=positive_phrases,
            negative_phrases=negative_phrases,
            user_reference=user_reference,
            user_reference_capitalized=user_reference_capitalized,
        )

        max_attempts = 4
        generated_reviews = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self._openai_client.send_request(prompt)

                start = response.find("{")
                end = response.rfind("}") + 1
                if start == -1 or end == 0:
                    logger.warning(f"JSON не найден в ответе (попытка {attempt})")
                    continue

                current_reviews = json.loads(response[start:end])

                if not all(
                    key in current_reviews for key in ["positive", "negative", "general"]
                ):
                    logger.warning(f"Не все ключи присутствуют (попытка {attempt})")
                    continue

                positive_text = current_reviews.get("positive", "")
                negative_text = current_reviews.get("negative", "")

                has_positive_tag = (
                    '<span class="positive">' in positive_text if positive_text else False
                )
                has_negative_tag = (
                    '<span class="negative">' in negative_text if negative_text else False
                )

                if (
                    positive_text
                    and negative_text
                    and has_positive_tag
                    and has_negative_tag
                ):
                    generated_reviews = current_reviews
                    logger.info("[ГЕНЕРАЦИЯ] Успешно сгенерированы отзывы")
                    break
                else:
                    logger.warning(f"Отсутствуют span-теги (попытка {attempt})")
                    if attempt == max_attempts:
                        generated_reviews = current_reviews

            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования JSON (попытка {attempt}): {e}")

        return generated_reviews

    def _format_representative_reviews(self, reviews: List[str]) -> str:
        """Форматирует репрезентативные отзывы для промпта."""
        return "\n".join(f"  - {r}" for r in reviews)

    async def _correct_reviews(
        self, generated_reviews: Dict[str, str]
    ) -> Dict[str, str]:
        """Корректирует грамматику сгенерированных отзывов."""
        if not generated_reviews or not any(generated_reviews.values()):
            return generated_reviews

        reviews_json_str = json.dumps(generated_reviews, ensure_ascii=False, indent=2)
        prompt = CORRECTION_PROMPT.format(reviews_json=reviews_json_str)

        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self._openai_client.send_request(prompt)

                start = response.find("{")
                end = response.rfind("}") + 1
                if start == -1 or end == 0:
                    logger.warning(
                        f"JSON не найден в ответе корректуры (попытка {attempt})"
                    )
                    continue

                corrected = json.loads(response[start:end])

                if all(
                    key in corrected for key in ["positive", "negative", "general"]
                ):
                    logger.info("[КОРРЕКТУРА] Успешно откорректированы отзывы")
                    return corrected
                else:
                    logger.warning(
                        f"Не все ключи присутствуют после корректуры (попытка {attempt})"
                    )

            except json.JSONDecodeError as e:
                logger.error(
                    f"Ошибка декодирования JSON при корректуре (попытка {attempt}): {e}"
                )

        return generated_reviews

    def _create_empty_summary(
        self, product_id: str, reviews: List[Review], params: Dict[str, Any]
    ) -> Summary:
        """Создаёт пустой Summary в случае ошибок."""
        ratings = [r.rating for r in reviews if r.rating is not None]
        rating_avg = sum(ratings) / len(ratings) if ratings else None

        dates = [r.review_date for r in reviews if r.review_date is not None]
        date_min = min(dates) if dates else None
        date_max = max(dates) if dates else None

        return Summary(
            product_id=UUID(product_id) if isinstance(product_id, str) else product_id,
            method=self.code,
            method_version=self.version,
            params=params,
            created_at=datetime.now(),
            reviews_count=len(reviews),
            rating_avg=rating_avg,
            date_min=date_min,
            date_max=date_max,
            text_overall=None,
            text_neutral=None,
            text_pros=None,
            text_cons=None,
            key_phrases=None,
        )
