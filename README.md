# Review Summarizer

Микросервис для суммаризации отзывов о продуктах с использованием больших языковых моделей. Анализирует отзывы с различных площадок (Ozon, Wildberries, Yandex и др.) и генерирует структурированные суммаризации.

## Возможности

- **Хранение данных**: Продукты, пользователи, отзывы с разных источников
- **Суммаризация**: Два метода - тестовый (stub) и LLM-based (OpenAI)
- **API**: REST API на FastAPI для интеграции
- **Веб-интерфейс**: Streamlit приложение для просмотра и генерации суммаризаций
- **Архитектура**: Упрощенная DDD с dependency injection

## Архитектура

Проект построен на принципах Domain-Driven Design:

- **Domain Layer**: Бизнес-логика (модели Product, User, Review, Summary)
- **Application Layer**: Координация use cases (сервисы для работы с продуктами, отзывами, суммаризацией)
- **Infrastructure Layer**: Технические детали (PostgreSQL, OpenAI API, репозитории)
- **Presentation Layer**: API (FastAPI) + UI (Streamlit)

## Технологии

- **Backend**: FastAPI, SQLAlchemy 2.0, asyncpg, Pydantic
- **База данных**: PostgreSQL
- **LLM**: OpenAI API (GPT)
- **UI**: Streamlit
- **Контейнеризация**: Docker, docker-compose
- **Зависимости**: dependency-injector, httpx, loguru

## Установка и запуск

1. **Клонировать репозиторий**:
```bash
git clone https://github.com/Shredian/review-summarizer.git
cd review-summarizer
```

2. **Настроить окружение**:
```bash
cp .env.example .env
# Настроить переменные в .env
```

3. **Запустить через Docker**:
```bash
docker compose up --build
```

Сервис будет доступен:
- **API**: http://localhost:8000
- **Документация API**: http://localhost:8000/docs
- **Streamlit UI**: http://localhost:8501

## Конфигурация

Основные настройки в `.env`:
- `APP_DATABASE_URL`: URL PostgreSQL базы
- `APP_OPENAI_API_KEY`: Ключ OpenAI API
- `APP_API_HOST`/`APP_API_PORT`: Настройки API сервера


## Методы суммаризации

### Stub Method
Тестовый метод для разработки. Возвращает предопределенные данные без реального анализа.

### LLM Method
Полноценная суммаризация на базе OpenAI:
- Фильтрация полезных отзывов
- Извлечение ключевых фраз
- Анализ тональности
- Генерация структурированных суммаризаций (плюсы/минусы/нейтральное)

## Структура данных

- **Product**: Информация о продукте
- **Review**: Отзыв с метаданными источника (source, url, rating, text)
- **Summary**: Результат суммаризации с ключевыми фразами и текстами
- **User**: Автор отзыва (опционально)
