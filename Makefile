.PHONY: dev prod worker beat frontend test lint clean install migrations seed help

help:
	@echo "GeoMarketGPT Commands"
	@echo "======================"
	@echo "make dev         - Start development server (hot reload)"
	@echo "make prod        - Start production server"
	@echo "make worker      - Start Celery worker"
	@echo "make beat        - Start Celery beat scheduler"
	@echo "make frontend    - Start Streamlit frontend"
	@echo "make test        - Run test suite"
	@echo "make lint        - Run linters"
	@echo "make clean        - Clean cache and temporary files"
	@echo "make install     - Install dependencies"
	@echo "make migrations  - Run database migrations"
	@echo "make seed        - Seed sample data"

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

prod:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --limit-max-requests 10000 --timeout-keep-alive 30

worker:
	celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

beat:
	celery -A app.workers.celery_app beat --loglevel=info

frontend:
	cd frontend && streamlit run app.py --server.port=8501 --server.address=0.0.0.0

test:
	python -m pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	ruff check app/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage coverage.xml htmlcov/ .mypy_cache/ .ruff_cache/

install:
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -e ".[dev]"

migrations:
	alembic upgrade head

seed:
	python scripts/seed_data.py --all
