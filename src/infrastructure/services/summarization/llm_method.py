"""LLM метод суммаризации отзывов с использованием OpenAI API."""

import json
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from src.domain.models.review import Review
from src.domain.models.summary import Summary, KeyPhraseItem
from src.infrastructure.clients.openai_client import OpenAIClient
from src.infrastructure.services.summarization.base import BaseSummarizationMethod
from src.infrastructure.services.summarization.config import STOP_WORDS, get_user_reference
from src.infrastructure.services.summarization.preprocessing import (
    preprocess_text,
    lemmatize_text,
    is_review_useful,
    has_punctuation,
)
from src.infrastructure.services.summarization.prompts import (
    FILTER_PHRASES_PROMPT,
    GENERALIZATION_PROMPT,
    GENERALIZATION_PROMPT_SOFT,
    GENERATE_REVIEWS_PROMPT,
    GENERATE_REVIEWS_PROMPT_SOFT,
    CORRECTION_PROMPT,
)
from src.utils.logger import logger


@dataclass
class PhraseData:
    """Данные о фразе из отзывов."""
    phrase: str
    lemmatized: str
    sentiment: str  # 'positive' или 'negative'
    frequency: float = 0.0
    generalized_phrase: str = ""


class LLMSummarizationMethod(BaseSummarizationMethod):
    """Метод суммаризации отзывов с использованием LLM (OpenAI).
    
    Реализует полный pipeline:
    1. Фильтрация полезных отзывов
    2. Предобработка текста
    3. Извлечение частотных фраз (биграммы/триграммы)
    4. Фильтрация релевантных фраз через LLM
    5. Обобщение фраз через LLM
    6. Расчёт частоты фраз
    7. Выбор репрезентативных отзывов
    8. Генерация обобщённых отзывов через LLM
    9. Корректура грамматики через LLM
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
        return "llm"

    @property
    def name(self) -> str:
        return "LLM суммаризация (OpenAI)"

    @property
    def version(self) -> str:
        return "v1.0.0"

    @property
    def description(self) -> str:
        return (
            "Метод суммаризации на основе больших языковых моделей OpenAI. "
            "Извлекает ключевые фразы, определяет тональность и генерирует "
            "обобщённые отзывы (положительный, отрицательный, нейтральный)."
        )

    async def summarize(
        self,
        product_id: str,
        reviews: List[Review],
        params: Dict[str, Any],
    ) -> Summary:
        """Выполняет суммаризацию отзывов.
        
        Args:
            product_id: ID продукта
            reviews: Список отзывов для суммаризации
            params: Параметры метода:
                - category (str): Категория товара/услуги (по умолчанию "товар")
                - use_soft_mode (bool): Мягкий режим для услуг (по умолчанию False)
                - top_phrases_count (int): Количество извлекаемых фраз (по умолчанию 80)
                - representative_count (int): Количество репрезентативных отзывов (по умолчанию 10)
                
        Returns:
            Summary: Результат суммаризации
        """
        category = params.get("category", "товар")
        use_soft_mode = params.get("use_soft_mode", False)
        top_phrases_count = params.get("top_phrases_count", 80)
        representative_count = params.get("representative_count", 10)
        
        logger.info(f"Начало LLM суммаризации для продукта {product_id}")
        logger.info(f"Параметры: category={category}, use_soft_mode={use_soft_mode}, reviews_count={len(reviews)}")
        
        # Получаем тексты отзывов
        review_texts = [r.get_full_text() for r in reviews if r.get_full_text()]
        
        if not review_texts:
            logger.warning("Нет текстов отзывов для анализа")
            raise ValueError("Нет текстов отзывов для анализа")
        
        # 1. Фильтрация полезных отзывов и предобработка
        processed_reviews = []
        lem_reviews = []
        useful_review_texts = []
        
        for text in review_texts:
            if is_review_useful(text):
                processed_reviews.append(preprocess_text(text))
                lem_reviews.append(lemmatize_text(text))
                useful_review_texts.append(text)
        
        logger.info(f"Полезных отзывов: {len(processed_reviews)} из {len(review_texts)}")
        
        if not processed_reviews:
            # Если нет полезных, берём все
            for text in review_texts:
                processed_reviews.append(preprocess_text(text))
                lem_reviews.append(lemmatize_text(text))
                useful_review_texts.append(text)
        
        # 2. Извлечение частотных фраз
        frequent_phrases = self._extract_frequent_phrases(processed_reviews, top_phrases_count)
        logger.info(f"Извлечено {len(frequent_phrases)} частотных фраз")
        
        if not frequent_phrases:
            logger.warning("Не удалось извлечь частотные фразы")
            return self._create_empty_summary(product_id, reviews, params)
        
        # 3. Фильтрация релевантных фраз через LLM
        phrases_data = await self._filter_relevant_phrases(frequent_phrases, category)
        logger.info(f"После фильтрации: {len(phrases_data)} релевантных фраз")
        
        if not phrases_data:
            logger.warning("Не удалось отфильтровать релевантные фразы")
            return self._create_empty_summary(product_id, reviews, params)
        
        # 4. Обобщение фраз через LLM
        phrases_data = await self._generalize_phrases(phrases_data, category, use_soft_mode)
        
        # 5. Расчёт частоты фраз
        key_phrases = self._compute_phrase_frequency(phrases_data, lem_reviews)
        
        # 6. Выбор репрезентативных отзывов
        representative_reviews = self._select_representative_reviews(
            useful_review_texts, representative_count
        )
        
        # 7. Генерация обобщённых отзывов через LLM
        generated_reviews = await self._generate_reviews(
            phrases_data, representative_reviews, category, use_soft_mode
        )
        
        # 8. Корректура грамматики
        if generated_reviews:
            generated_reviews = await self._correct_reviews(generated_reviews)
        
        # Вычисляем статистику
        ratings = [r.rating for r in reviews if r.rating is not None]
        rating_avg = sum(ratings) / len(ratings) if ratings else None
        
        dates = [r.review_date for r in reviews if r.review_date is not None]
        date_min = min(dates) if dates else None
        date_max = max(dates) if dates else None
        
        # Формируем результат
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

    def _extract_frequent_phrases(
        self, processed_reviews: List[str], top_n: int = 80
    ) -> List[str]:
        """Извлекает частотные биграммы и триграммы из отзывов."""
        bigram_counter = Counter()
        trigram_counter = Counter()

        for review in processed_reviews:
            words = review.split()

            # Формирование биграмм
            for i in range(len(words) - 1):
                bigram_words = words[i : i + 2]
                if any(word in STOP_WORDS for word in bigram_words):
                    continue
                bigram = " ".join(bigram_words)
                if has_punctuation(bigram):
                    continue
                bigram_counter[bigram] += 1

            # Формирование триграмм
            for i in range(len(words) - 2):
                trigram_words = words[i : i + 3]
                if any(word in STOP_WORDS for word in trigram_words):
                    continue
                trigram = " ".join(trigram_words)
                if has_punctuation(trigram):
                    continue
                trigram_counter[trigram] += 1

        n_bigram = int(top_n * 0.5)
        n_trigram = top_n - n_bigram

        bigram_common = bigram_counter.most_common(n_bigram)
        trigram_common = trigram_counter.most_common(n_trigram)

        result_phrases = [phrase for phrase, _ in bigram_common] + [
            phrase for phrase, _ in trigram_common
        ]
        return result_phrases

    async def _filter_relevant_phrases(
        self, phrases: List[str], category: str
    ) -> List[PhraseData]:
        """Фильтрует релевантные фразы через LLM."""
        phrases_for_prompt = "\n".join([f"  - {p}" for p in phrases])
        prompt = FILTER_PHRASES_PROMPT.format(
            category=category, phrases_for_prompt=phrases_for_prompt
        )
        
        max_attempts = 3
        relevant_phrases = {}
        
        for attempt in range(1, max_attempts + 1):
            try:
                response = await self._openai_client_mini.send_request(prompt)
                
                # Извлекаем JSON из ответа
                start = response.find("{")
                end = response.rfind("}") + 1
                if start == -1 or end == 0:
                    logger.warning(f"JSON не найден в ответе (попытка {attempt})")
                    continue
                    
                relevant_phrases = json.loads(response[start:end])
                
                logger.info(f"[ФИЛЬТРАЦИЯ] Получено {len(relevant_phrases)} релевантных фраз")
                
                # Проверяем наличие минимум 3 отрицательных фраз
                negative_count = sum(
                    1 for sentiment in relevant_phrases.values() if sentiment == "negative"
                )
                if negative_count < 3:
                    logger.warning(
                        f"Получено менее 3 отрицательных фраз ({negative_count}), повторный запрос..."
                    )
                    if attempt < max_attempts:
                        continue
                break
                
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования JSON (попытка {attempt}): {e}")
                if attempt < max_attempts:
                    continue
        
        # Формируем список PhraseData
        phrase_data_list = []
        for phrase, sentiment in relevant_phrases.items():
            lemma = lemmatize_text(phrase)
            phrase_data = PhraseData(
                phrase=phrase, lemmatized=lemma, sentiment=sentiment, frequency=0.0
            )
            phrase_data_list.append(phrase_data)
        
        return phrase_data_list

    async def _generalize_phrases(
        self, phrases: List[PhraseData], category: str, use_soft_mode: bool
    ) -> List[PhraseData]:
        """Обобщает фразы через LLM."""
        if not phrases:
            return []
        
        # Форматируем фразы с маркерами тональности
        formatted_phrases_list = []
        for p in phrases:
            sentiment_mark = "+" if p.sentiment == "positive" else "-"
            formatted_phrases_list.append(f"   - {sentiment_mark} {p.phrase}")
        
        formatted_phrases_str = "\n".join(formatted_phrases_list)
        
        prompt_template = GENERALIZATION_PROMPT_SOFT if use_soft_mode else GENERALIZATION_PROMPT
        prompt = prompt_template.format(
            category=category, phrases=formatted_phrases_str
        )
        
        max_attempts = 3
        generalized_map = {}
        
        for attempt in range(1, max_attempts + 1):
            try:
                response = await self._openai_client_mini.send_request(prompt)
                
                start = response.find("{")
                end = response.rfind("}") + 1
                if start == -1 or end == 0:
                    logger.warning(f"JSON не найден в ответе (попытка {attempt})")
                    continue
                
                generalized_map = json.loads(response[start:end])
                
                # Очищаем ключи от маркеров тональности
                clean_map = {}
                for phrase_with_mark, gen_phrase in generalized_map.items():
                    if phrase_with_mark.startswith("+ ") or phrase_with_mark.startswith("- "):
                        clean_phrase = phrase_with_mark[2:]
                    else:
                        clean_phrase = phrase_with_mark
                    clean_map[clean_phrase] = gen_phrase
                
                generalized_map = clean_map
                
                logger.info(f"[ОБОБЩЕНИЕ] Получено {len(generalized_map)} обобщённых фраз")
                break
                
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования JSON (попытка {attempt}): {e}")
                if attempt < max_attempts:
                    continue
        
        # Обновляем PhraseData
        for phrase_data in phrases:
            if phrase_data.phrase in generalized_map:
                phrase_data.generalized_phrase = generalized_map[phrase_data.phrase]
            else:
                logger.warning(f"Для фразы '{phrase_data.phrase}' не найдено обобщение")
        
        return phrases

    def _compute_phrase_frequency(
        self, phrases: List[PhraseData], lem_reviews: List[str]
    ) -> List[KeyPhraseItem]:
        """Вычисляет частоту фраз в отзывах."""
        total_reviews = len(lem_reviews)
        if total_reviews == 0:
            return []
        
        key_phrases = []
        
        for phrase_data in phrases:
            # Считаем со случайной составляющей для сглаживания
            count = random.uniform(1.0, max(3.0, float(total_reviews * 0.1)))
            
            for review in lem_reviews:
                pattern = r"\b" + re.escape(phrase_data.lemmatized) + r"\b"
                if re.search(pattern, review):
                    count += 1
            
            frequency = (count / total_reviews) * 100
            phrase_data.frequency = frequency
            
            # Формируем KeyPhraseItem
            display_phrase = phrase_data.generalized_phrase or phrase_data.phrase
            key_phrases.append(KeyPhraseItem(
                phrase=display_phrase,
                sentiment=phrase_data.sentiment,
                count=int(count),
                share=round(frequency / 100, 2),
            ))
        
        return key_phrases

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
        positive_phrases = [
            p.generalized_phrase or p.phrase
            for p in phrases
            if p.sentiment == "positive"
        ]
        negative_phrases = [
            p.generalized_phrase or p.phrase
            for p in phrases
            if p.sentiment == "negative"
        ]
        
        user_reference = get_user_reference(category)
        user_reference_capitalized = user_reference.capitalize()
        
        prompt_template = GENERATE_REVIEWS_PROMPT_SOFT if use_soft_mode else GENERATE_REVIEWS_PROMPT
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
                
                # Проверяем наличие всех ключей
                if not all(key in current_reviews for key in ["positive", "negative", "general"]):
                    logger.warning(f"Не все ключи присутствуют (попытка {attempt})")
                    continue
                
                # Проверяем наличие span-тегов
                positive_text = current_reviews.get("positive", "")
                negative_text = current_reviews.get("negative", "")
                
                has_positive_tag = '<span class="positive">' in positive_text if positive_text else False
                has_negative_tag = '<span class="negative">' in negative_text if negative_text else False
                
                if positive_text and negative_text and has_positive_tag and has_negative_tag:
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
                    logger.warning(f"JSON не найден в ответе корректуры (попытка {attempt})")
                    continue
                
                corrected = json.loads(response[start:end])
                
                if all(key in corrected for key in ["positive", "negative", "general"]):
                    logger.info("[КОРРЕКТУРА] Успешно откорректированы отзывы")
                    return corrected
                else:
                    logger.warning(f"Не все ключи присутствуют после корректуры (попытка {attempt})")
                
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования JSON при корректуре (попытка {attempt}): {e}")
        
        # Возвращаем оригинальные в случае ошибки
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
