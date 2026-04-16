#!/bin/bash
set -e

alembic upgrade head

APP_MODE="${APP_MODE:-api}"

if [ "$APP_MODE" = "streamlit" ]; then
  exec streamlit run src/presentation/streamlit/app.py --server.port=8501 --server.address=0.0.0.0
fi

exec uvicorn src.presentation.server.server:app --host 0.0.0.0 --port "${APP_API_PORT:-8000}"
