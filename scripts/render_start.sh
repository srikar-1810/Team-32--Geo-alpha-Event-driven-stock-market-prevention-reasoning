#!/bin/bash
# Exit on error
set -e

# 1. Run Database Migrations (if any)
# python -m alembic upgrade head

# 2. Start Celery Worker in the background
echo "Starting Celery Worker..."
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 &

# 3. Start FastAPI API using Uvicorn
echo "Starting FastAPI API..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
