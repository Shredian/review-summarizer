FROM python:3.12-slim
      
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgomp1 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG INSTALL_RESEARCH=1

COPY requirements.txt .
COPY requirements.research.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN if [ "$INSTALL_RESEARCH" = "1" ]; then pip install --no-cache-dir -r requirements.research.txt; fi

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
