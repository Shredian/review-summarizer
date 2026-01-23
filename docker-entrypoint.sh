#!/bin/bash
set -e

alembic upgrade head
exec streamlit run src/presentation/streamlit/app.py --server.port=8501 --server.address=0.0.0.0
