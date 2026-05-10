# syntax=docker/dockerfile:1.4

FROM python:3.14-slim

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgomp1 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

RUN python -m spacy download ru_core_news_sm

COPY src/ ./src/
COPY alembic.ini .
COPY migrations/ ./migrations/

RUN mkdir -p /app/logs

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8501

ENTRYPOINT ["/bin/bash", "/docker-entrypoint.sh"]
