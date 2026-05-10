# Review Summarizer

Сервис для анализа и суммаризации отзывов о товарах (маркетплейсы и аналогичные источники): хранение продуктов и отзывов, несколько методов суммаризации, в том числе пайплайн с аспектами и опорой на цитаты из отзывов, подсказки при написании нового отзыва на основе профиля пользователя и продукта, а также модуль **evaluation** (бенчмарки, метрики, отчёты).

## Возможности

- **Данные:** продукты, пользователи, отзывы с привязкой к источнику.
- **Суммаризация:** зарегистрированные методы (см. таблицу ниже), сохранение результатов и артефактов пайплайна в БД.
- **Подсказки отзывов:** фоновое построение профилей по истории отзывов (очередь и кэш в **Redis**), выдача подсказок через API и Streamlit.
- **API:** REST на **FastAPI**, документация OpenAPI.
- **Интерфейс:** **Streamlit** — обзор продуктов и отзывов, запуск суммаризации, история, визуализация aspect/evidence, подсказки.
- **Evaluation:** загрузка бенчмарк-наборов, прогон метрик и судей (включая LLM-judge), экспорт отчётов — через **Streamlit** (страница *Evaluation Metrics*) и HTTP API.

## Технологии

**Backend:** FastAPI, SQLAlchemy 2 (async), asyncpg, Pydantic, dependency-injector, Alembic.  
**Хранилища:** PostgreSQL, Redis.  
**LLM:** OpenAI API, LangChain (в зависимостях).  
**NLP:** spaCy (в образе подтягивается русская модель), sklearn, sentence-transformers, KeyBERT, BERTopic и связанные библиотеки для воркера подсказок.  
**UI / аналитика:** Streamlit, Plotly, pandas; для evaluation — matplotlib, BERTScore, ROUGE и др. (см. [requirements.txt](requirements.txt)).

Зависимости перечислены в одном файле [requirements.txt](requirements.txt): приложение, воркер, evaluation и **ruff** для разработки.

Локально (без Docker):

```bash
pip install -r requirements.txt
```

Рекомендуемая версия Python для локальной установки совместима с **Python 3.14** (как в Docker-образе).

## Быстрый старт: весь стек в Docker

Один запуск поднимает **PostgreSQL**, **Redis**, **HTTP API**, **Streamlit** и **воркер подсказок** — все рабочие части проекта из одного файла [docker-compose.yml](docker-compose.yml).

1. Склонируйте репозиторий и перейдите в каталог проекта.

2. При необходимости создайте `.env` из примера (для Docker достаточно значений по умолчанию в `docker-compose`; для LLM задайте ключ OpenAI):

   ```bash
   cp .env.example .env
   ```

   Подробнее о переменных — в [.env.example](.env.example) и в [src/utils/config.py](src/utils/config.py).

3. Запуск:

   ```bash
   docker compose up --build
   ```

При старте контейнеров выполняется `alembic upgrade head` (актуальная схема БД).

**Адреса по умолчанию:**

| Что | URL |
|-----|-----|
| API | http://localhost:8000 |
| OpenAPI (Swagger) | http://localhost:8000/docs |
| Streamlit | http://localhost:8501 |

Порты БД и Redis, а также порт API и Streamlit при необходимости переопределяются переменными окружения хоста (см. `docker-compose.yml`: `POSTGRES_PORT`, `REDIS_PORT`, `APP_API_PORT`, `APP_STREAMLIT_PORT`).

## Переменные окружения (кратко)

- `APP_DATABASE_URL` — строка подключения к PostgreSQL (asyncpg). В Compose задаётся автоматически для сервисов приложения.
- `APP_REDIS_URL` — Redis (в Compose по умолчанию `redis://redis:6379/0`).
- `APP_OPENAI_API_KEY`, `APP_OPENAI_MODEL`, `APP_OPENAI_MODEL_MINI` — доступ к OpenAI для LLM-слоёв суммаризации и evaluation.
- `APP_PUBLIC_API_BASE_URL` — базовый URL API для Streamlit (с хоста по умолчанию `http://localhost:8000`).
- `APP_LOG_LEVEL`, `APP_API_PORT`, `APP_STREAMLIT_PORT` — логирование и порты.
- `APP_REVIEW_SUGGESTIONS_EMBEDDING_MODEL` — модель эмбеддингов для воркера подсказок (см. сервис `review_suggestions_worker` в Compose).

Учётные данные Postgres в Compose: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.

## Модули и интерфейсы

- **REST API** — префикс `/api/v1`, роуты собираются из [src/presentation/server/api/v1/](src/presentation/server/api/v1/): продукты, отзывы, суммаризация, подсказки, **evaluation** и др.
- **Evaluation по HTTP** — например запуск прогона: `POST /api/v1/evaluation/run` (тело запроса — параметры набора, опционально `product_limit`, флаги judge/метрик; см. [src/presentation/server/api/v1/evaluation_api.py](src/presentation/server/api/v1/evaluation_api.py)).
- **Evaluation в Streamlit** — страница *Evaluation Metrics*: обзор наборов без подгрузки отзывов, вставка небольшого JSON в БД, прогон с ограничением числа товаров и без тяжёлых метрик по умолчанию.

- **Тесты** не входят в Docker-образ; каталог `tests/` в контекст сборки не передаётся. Запуск локально после установки зависимостей:

  ```bash
  pytest
  ```

## Архитектура кода

Ориентация на упрощённый Domain-Driven Design и явный контейнер зависимостей ([src/container.py](src/container.py)):

| Слой | Каталог | Назначение |
|------|---------|------------|
| Domain | [src/domain/](src/domain/) | Модели, доменная логика, DTO evaluation и подсказок |
| Application | [src/application/](src/application/) | Сценарии: продукты, отзывы, суммаризация, подсказки, evaluation |
| Infrastructure | [src/infrastructure/](src/infrastructure/) | БД, Redis, клиенты, реализации суммаризации, NLP, evaluation |
| Presentation | [src/presentation/](src/presentation/) | FastAPI, Streamlit |
| Workers | [src/workers/](src/workers/) | Фоновый воркер профилей подсказок |

Дополнительные материалы для разработчиков: [docs/README.md](docs/README.md).

## Методы суммаризации

Идентификаторы методов задаются в [src/container.py](src/container.py) (`summarization_methods`).

| Ключ | Описание |
|------|----------|
| `stub` | Заглушка: заранее заданные данные без реального анализа |
| `llm` | Суммаризация через LLM: отбор отзывов, ключевые фразы, тональность, блоки плюсов/минусов/нейтрального |
| `aspect` | Метод с опорой на аспекты и LLM |
| `aspect_evidence_guided_v1` | Пайплайн: упоминания аспектов, кластеры, evidence и план генерации; опциональное уточнение через LLM при включённых параметрах и ключе API |

Артефакты aspect/evidence сохраняются в отдельных таблицах (см. миграции Alembic в [migrations/](migrations/)).

## Структура данных (кратко)

- **Product** — товар.
- **Review** — отзыв (источник, ссылка, рейтинг, текст).
- **Summary** — результат суммаризации.
- **User** — автор отзыва (по необходимости).
- Профили и события подсказок — домен [src/domain/review_suggestions/](src/domain/review_suggestions/) и соответствующие таблицы в БД.
