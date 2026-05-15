#!/bin/bash
set -e

echo "🚀 Starting GeoMarketGPT All-in-One Production Stack..."

# 1. Start Redis
echo "📥 Starting Redis..."
redis-server --port 6379 --daemonize yes || echo "Redis might be already running"

# 2. Start PostgreSQL
echo "🐘 Initializing PostgreSQL Data Folder..."
export PGDATA=/app/postgres_data
if [ ! -d "$PGDATA" ]; then
    mkdir -p "$PGDATA"
    initdb -D "$PGDATA"
fi

echo "🐘 Starting PostgreSQL..."
pg_ctl -D "$PGDATA" -o "-c unix_socket_directories='/tmp'" -l /app/postgres_log start || echo "Postgres might be already running"

# Wait for Postgres
echo "Waiting for Postgres to wake up..."
sleep 5

# 3. Start ChromaDB (Vector Store)
echo "🧠 Starting ChromaDB..."
chroma run --path /app/chroma_data --host 0.0.0.0 --port 8001 &
export CHROMA_PORT=8001

# Wait for ChromaDB to be ready
echo "Waiting for ChromaDB to wake up..."
sleep 10

# 4. Initialize Database
echo "🔧 Running database initialization..."
# psql uses standard postgresql://
psql -h localhost -d postgres -c "CREATE DATABASE geomarketgpt;" || echo "Database might exist"

# API env vars
export DATABASE_URL=postgresql+asyncpg://localhost:5432/postgres
export REDIS_URL=redis://localhost:6379/0
export CHROMA_HOST=localhost
export CHROMA_PORT=8001

python -m scripts.seed_data || echo "Seeding failed, continuing anyway..."

# 5. Start the API Server (FastAPI)
echo "⚡ Starting FastAPI Backend..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# 6. Start the Celery Worker
echo "👷 Starting Celery Worker..."
celery -A app.workers.celery_app worker --loglevel=info &

# 7. Start the Frontend (Streamlit)
echo "🌍 Launching Streamlit Dashboard on Port 7860..."
streamlit run frontend/app.py --server.port 7860 --server.address 0.0.0.0
