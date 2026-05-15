#!/usr/bin/env bash
set -euo pipefail

APP_NAME="GeoMarketGPT"
echo "[${APP_NAME}] Initializing database..."

# Create database if it doesn't exist
psql -U geogpt -h localhost -tc "SELECT 1 FROM pg_database WHERE datname = 'geomarket_gpt'" | grep -q 1 || \
    psql -U geogpt -h localhost -c "CREATE DATABASE geomarket_gpt"

# Run migrations
echo "Running Alembic migrations..."
alembic upgrade head

# Seed sample data
echo "Seeding sample data..."
python scripts/seed_data.py --all

echo "[${APP_NAME}] Database initialization complete."
