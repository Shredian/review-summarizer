from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    MentionExtractionResult,
    ReviewSpan,
    SentimentLabel,
)


POSITIVE_MARKERS = (
    "хорош",  # хорошие, хорошо, хорошее, хорошая, хороши, лучш, прехорош
    "отлич",  # отлично, отличный, отличная
    "супер",  # супер, суперский, суперская
    "прекрасн",  # прекрасно, прекрасный, прекрасная
    "замечательн",  # замечательный, замечательно
    "идеальн",  # идеально, идеальный, идеальна
    "удоб",  # удобно, удобный, удобная
    "комфорт",  # комфортно, комфортный
    "эмоциональн",  # эмоционально, эмоциональный
    "качеств",  # качество, качественный, качественно
    "прият",  # приятно, приятный
    "эффектив",  # эффективно, эффективный
    "быстр",  # быстро, быстрый, быстрота
    "шикарн",  # шикарно, шикарный
    "классн",  # классно, классный
    "выгод",  # выгодно, выгодный
    "легк",  # легко, легкий, легкость
    "надёжн",  # надёжно, надёжный
    "стабильн",  # стабильно, стабильный
    "аккуратн",  # аккуратно, аккуратный
    "ярк",  # ярко, яркий
    "прост",  # просто, простой, простота
    "полезн",  # полезный, полезно
    "доступн",  # доступно, доступный
    "современ",  # современный, современно
    "красив",  # красиво, красивый
    "чист",  # чисто, чистый
    "функциональн",  # функционально, функциональный
    "прият",  # приятно, приятный, приятная
    "прочные",  # прочный, прочная, прочные
    "эргономичн",  # эргономично, эргономичный
    "экономичн",  # экономичные, экономично
    "вкусн",  # вкусно, вкусный
    "нрав",  # нравится, нравиться, понравилось, понравился, понравилась, понравились
    "рекоменд",  # рекомендую, рекомендуем
    "окуп",  # окупился, окупилась, окупились
    "поразил",  # поразительно, поразил, поразила
    "великолеп",  # великолепно, великолепный
    "а++++",  # любые маркеры “супер-отзывов”
    "добр",  # добрый, доброжелательный, доброжелательно
    "устроил",  # устроило, устроил
    "удовлетвор",  # удовлетворен, удовлетворила, удовлетворение
)

NEGATIVE_MARKERS = (
    "плох",  # плохо, плохой, плохая
    "ужасн",  # ужасно, ужасный, кошмарный
    "безобразн",  # безобразный, безобразно
    "отврат",  # отвратительный, отвратно
    "разочарова",  # разочарован, разочарование
    "катастроф",  # катастрофа, катастрофический
    "жаль",  # жаль, жалею, сожаление
    "досад",  # досадно, досада
    "раздраж",  # раздражает, раздражение
    "медлен",  # медленно, медленный
    "неудоб",  # неудобно, неудобный
    "скуч",  # скучный, скучно
    "слишком",  # слишком
    "слож",  # сложно, сложный
    "лома",  # ломается, ломался, сломался, поломка
    "слом",  # сломано, сломался, сломанная
    "брак",  # брак, бракованный, браковано
    "дефект",  # дефект, дефектный
    "проблем",  # проблема, проблемы, проблемный
    "глюч",  # глючит, глюк, глючный
    "требует",  # требует доработки, требует внимательности
    "дорог",  # дорого, дорогой, дорогая
    "низк",  # низкое качество, низкий
    "полом",  # поломанный, поломка
    "грязн",  # грязный, грязно
    "шумн",  # шумный, шумно
    "некачеств",  # некачественный, некачественно
    "неприят",  # неприятный, неприятно
    "устал",  # усталость, устал
    "обман",  # обман, обманули
    "ненадёжн",  # ненадёжно, ненадёжный
    "слаб",  # слабый, слабо
    "разбит",  # разбит, разбито, разбита
    "треснут",  # треснуто, треснутый
    "испорт",  # испорчен, испортился
    "теря",  # теряется, теряет
    "грел",  # греется, перегревается
    "опасн",  # опасный, опасно
    "раздраж",  # раздражающий, раздражало
    "подвод",  # подводит, подвёл, подвела
    "долг",  # долго, долгий
    "устаревш",  # устаревший, устарело
    "огранич",  # ограничение, ограничено
    "отказ",  # отказ, отказал
    "запах",  # запах неприятный
    "завис",  # завис, зависает
    "теряются",  # теряются, потерялись
    "трудн",  # трудно, трудный
)


class BaseMentionExtractor(ABC):
    """Pluggable интерфейс extraction стадии."""

    @property
    @abstractmethod
    def version(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def extract(
        self,
        spans: Iterable[ReviewSpan],
        aspect_candidates: list[str],
    ) -> list[MentionExtractionResult]:
        raise NotImplementedError


class HeuristicMentionExtractor(BaseMentionExtractor):
    """Детерминированный extractor для traceable baseline этапа."""

    @property
    def version(self) -> str:
        return "heuristic_v1"

    def extract(
        self,
        spans: Iterable[ReviewSpan],
        aspect_candidates: list[str],
    ) -> list[MentionExtractionResult]:
        mentions: list[MentionExtractionResult] = []
        sorted_candidates = sorted(
            {candidate.strip().lower() for candidate in aspect_candidates if candidate.strip()},
            key=len,
            reverse=True,
        )
        for span in spans:
            sentiment, score = self._sentiment_for_span(span.normalized_text)
            matched = [candidate for candidate in sorted_candidates if candidate in span.normalized_text]
            for candidate in matched[:3]:
                mentions.append(
                    MentionExtractionResult(
                        review_id=span.review_id,
                        section_type=span.section_type,
                        span_text=span.span_text,
                        aspect_raw=candidate,
                        aspect_candidate=candidate,
                        sentiment_label=sentiment,
                        sentiment_score=score,
                        extractor_confidence=0.75 if sentiment != SentimentLabel.NEUTRAL else 0.55,
                    )
                )
        return mentions

    def _sentiment_for_span(self, normalized_span: str) -> tuple[SentimentLabel, float]:
        positive_hits = sum(1 for marker in POSITIVE_MARKERS if marker in normalized_span)
        negative_hits = sum(1 for marker in NEGATIVE_MARKERS if marker in normalized_span)
        if positive_hits and negative_hits:
            return SentimentLabel.MIXED, 0.0
        if positive_hits:
            return SentimentLabel.POSITIVE, min(1.0, 0.5 + positive_hits * 0.1)
        if negative_hits:
            return SentimentLabel.NEGATIVE, max(-1.0, -0.5 - negative_hits * 0.1)
        return SentimentLabel.NEUTRAL, 0.0
