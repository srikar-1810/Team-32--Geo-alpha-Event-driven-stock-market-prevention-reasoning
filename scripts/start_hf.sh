#!/bin/bash
set -e

echo "🚀 Starting GeoMarketGPT All-in-One Production Stack..."

# 1. Start Redis
echo "📥 Starting Redis..."
redis-server --daemonize yes

# 2. Start PostgreSQL
echo "🐘 Starting PostgreSQL..."
service postgresql start

# Wait for Postgres to be ready
until pg_isready; do
  echo "Waiting for Postgres..."
  sleep 2
done

# 3. Initialize Database
echo "🔧 Running database initialization..."
# Hugging Face runs as user 1000, so we might need to handle postgres permissions
su - postgres -c "psql -c \"CREATE DATABASE geomarketgpt;\"" || true
su - postgres -c "psql -c \"ALTER USER postgres WITH PASSWORD 'postgres';\"" || true

# Run migrations
bash scripts/init_db.sh

# 4. Start the API Server (FastAPI) in the background
echo "⚡ Starting FastAPI Backend..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# 5. Start the Celery Worker (for background data ingestion)
echo "👷 Starting Celery Worker..."
celery -A app.workers.celery_app worker --loglevel=info &

# 6. Start the Frontend (Streamlit)
# Hugging Face expects the app on port 7860
echo "🌍 Launching Streamlit Dashboard on Port 7860..."
streamlit run frontend/app.py --server.port 7860 --server.address 0.0.0.0
