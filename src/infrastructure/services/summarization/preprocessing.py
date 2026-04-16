"""Предобработка текста для суммаризации отзывов."""

import re
import string
from typing import List, Optional, Tuple, TYPE_CHECKING

from src.infrastructure.services.summarization.config import STOP_WORDS

if TYPE_CHECKING:
    from src.domain.models.review import Review

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        try:
            _nlp = spacy.load("ru_core_news_sm")
        except OSError:
            # Модель не установлена, нужно скачать
            from spacy.cli import download
            download("ru_core_news_sm")
            _nlp = spacy.load("ru_core_news_sm")
    return _nlp


def preprocess_text(text: str) -> str:
    text = text.lower()
    # Сохраняем буквы (латиница + кириллица), пробелы и основные знаки препинания
    text = re.sub(rf"[^{string.ascii_letters}а-яёА-ЯЁ\s\.\,\!\?]", "", text)
    # Убираем множественные пробелы
    text = re.sub(r"\s+", " ", text).strip()
    return text


def lemmatize_text(text: str) -> str:
    nlp = _get_nlp()
    text = text.lower()
    # Удаляем все кроме букв и пробелов
    text = re.sub(rf"[^{string.ascii_letters}а-яёА-ЯЁ\s]", "", text)
    doc = nlp(text)
    return " ".join(
        [
            token.lemma_
            for token in doc
            if token.is_alpha and token.lemma_ not in STOP_WORDS
        ]
    )


def is_review_useful(text: str) -> bool:
    score = 0

    # Эвристика 1: Минимальное число слов
    words = text.split()
    if len(words) >= 10:
        score += 1

    # Эвристика 2: Минимальное число предложений
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) >= 2:
        score += 1

    # Эвристика 3: Наличие ключевых слов для детализации
    detail_keywords = [
        "например",
        "конкретно",
        "особенно",
        "преимущество",
        "недостаток",
        "во-первых",
        "во-вторых",
        "главное",
        "плюс",
        "минус",
        "достоинство",
        "качество",
    ]
    if any(keyword in text.lower() for keyword in detail_keywords):
        score += 1

    # Эвристика 4: Плотность пунктуации (наличие нескольких запятых)
    if text.count(",") >= 2:
        score += 1

    # Эвристика 5: Наличие числовых данных
    if any(char.isdigit() for char in text):
        score += 1

    return score >= 3


def has_punctuation(phrase: str) -> bool:
    return bool(re.search(r"[{}]".format(re.escape(string.punctuation)), phrase))


def split_sentences(text: str) -> List[str]:
    """Разбивает текст на предложения по знакам препинания .!?"""
    if not text or not text.strip():
        return []
    sentences = re.split(r"[.!?]+", text)
    return [s.strip() for s in sentences if s.strip()]


def get_review_sentences_with_context(review: "Review") -> List[Tuple[str, Optional[str]]]:
    """Извлекает предложения из отзыва с указанием тональности.

    Returns:
        Список кортежей (предложение, тональность).
        Тональность: "positive" | "negative" | "neutral" | None
    """
    result: List[Tuple[str, Optional[str]]] = []

    def _sentiment_from_rating(rating: Optional[float]) -> Optional[str]:
        if rating is None:
            return "neutral"
        if rating >= 4:
            return "positive"
        if rating <= 2:
            return "negative"
        return "neutral"

    comment_sentiment = _sentiment_from_rating(review.rating)

    if review.plus:
        for sent in split_sentences(review.plus):
            if sent:
                result.append((sent, "positive"))

    if review.minus:
        for sent in split_sentences(review.minus):
            if sent:
                result.append((sent, "negative"))

    if review.comment:
        for sent in split_sentences(review.comment):
            if sent:
                result.append((sent, comment_sentiment))

    if review.title:
        for sent in split_sentences(review.title):
            if sent:
                result.append((sent, comment_sentiment))

    return result
