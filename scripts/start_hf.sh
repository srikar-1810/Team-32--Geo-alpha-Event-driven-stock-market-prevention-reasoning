#!/bin/bash
set -e

echo "🚀 Starting GeoMarketGPT All-in-One Production Stack..."

# 1. Start Redis in a way that doesn't need root
echo "📥 Starting Redis..."
redis-server --port 6379 --daemonize yes || echo "Redis might be already running"

# 2. Start PostgreSQL as the current user (HF user 1000)
echo "🐘 Initializing PostgreSQL Data Folder..."
export PGDATA=/app/postgres_data
if [ ! -d "$PGDATA" ]; then
    mkdir -p "$PGDATA"
    initdb -D "$PGDATA"
fi

echo "🐘 Starting PostgreSQL..."
pg_ctl -D "$PGDATA" -l /app/postgres_log start || echo "Postgres might be already running"

# Wait for Postgres to be ready
echo "Waiting for Postgres to wake up..."
sleep 5

# 3. Initialize Database Tables
echo "🔧 Running database initialization..."
psql -d postgres -c "CREATE DATABASE geomarketgpt;" || echo "Database might exist"
# Run your setup script
python -m scripts.seed_data || echo "Seeding failed, continuing anyway..."

# 4. Start the API Server (FastAPI) in the background
echo "⚡ Starting FastAPI Backend..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# 5. Start the Celery Worker
echo "👷 Starting Celery Worker..."
celery -A app.workers.celery_app worker --loglevel=info &

# 6. Start the Frontend (Streamlit) on Hugging Face port 7860
echo "🌍 Launching Streamlit Dashboard on Port 7860..."
streamlit run frontend/app.py --server.port 7860 --server.address 0.0.0.0
