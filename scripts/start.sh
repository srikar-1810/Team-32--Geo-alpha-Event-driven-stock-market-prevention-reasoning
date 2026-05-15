#!/usr/bin/env bash
set -euo pipefail

APP_NAME="GeoMarketGPT"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

print_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  dev           Start development environment (hot reload)"
    echo "  prod          Start production server"
    echo "  worker        Start Celery worker"
    echo "  beat          Start Celery beat scheduler"
    echo "  frontend      Start Streamlit frontend"
    echo "  all           Start everything via docker-compose"
    echo "  test          Run test suite"
    echo "  lint          Run linter"
    echo "  clean         Clean cache and temporary files"
    echo "  install       Install dependencies"
    echo "  migrations    Run database migrations"
    echo ""
}

case "${1:-help}" in
    dev)
        echo "[${APP_NAME}] Starting development server..."
        export APP_ENV=development
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
        ;;
    prod)
        echo "[${APP_NAME}] Starting production server..."
        uvicorn app.main:app \
            --host 0.0.0.0 \
            --port 8000 \
            --workers 4 \
            --limit-max-requests 10000 \
            --timeout-keep-alive 30 \
            --log-level info
        ;;
    worker)
        echo "[${APP_NAME}] Starting Celery worker..."
        celery -A app.workers.celery_app worker \
            --loglevel=info \
            --concurrency=4 \
            --max-tasks-per-child=200
        ;;
    beat)
        echo "[${APP_NAME}] Starting Celery beat scheduler..."
        celery -A app.workers.celery_app beat --loglevel=info
        ;;
    frontend)
        echo "[${APP_NAME}] Starting Streamlit frontend..."
        cd frontend
        streamlit run app.py \
            --server.port=8501 \
            --server.address=0.0.0.0
        ;;
    all)
        echo "[${APP_NAME}] Starting all services via docker-compose..."
        docker-compose up --build -d
        echo "Services started. Check status with 'docker-compose ps'"
        ;;
    test)
        echo "[${APP_NAME}] Running test suite..."
        python -m pytest tests/ -v --cov=app --cov-report=term-missing
        ;;
    lint)
        echo "[${APP_NAME}] Running linter..."
        ruff check app/ tests/
        ;;
    clean)
        echo "[${APP_NAME}] Cleaning cache..."
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete
        find . -type f -name "*.pyo" -delete
        find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
        rm -rf .coverage coverage.xml htmlcov/ .mypy_cache/ .ruff_cache/
        echo "Clean complete."
        ;;
    install)
        echo "[${APP_NAME}] Installing dependencies..."
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -e ".[dev]"
        echo "Dependencies installed."
        ;;
    migrations)
        echo "[${APP_NAME}] Running database migrations..."
        alembic upgrade head
        ;;
    help|*)
        print_usage
        ;;
esac
