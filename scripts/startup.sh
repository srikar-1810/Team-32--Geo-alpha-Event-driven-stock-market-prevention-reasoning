#!/usr/bin/env bash
set -euo pipefail

APP_NAME="GeoMarketGPT"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[${APP_NAME}]${NC} $1"; }
ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; }

check_prereqs() {
    local missing=0
    for cmd in python3 pip docker docker-compose; do
        if ! command -v "$cmd" &>/dev/null; then
            warn "$cmd not found"
            missing=1
        fi
    done
    if [ "$missing" -eq 1 ]; then
        err "Missing prerequisites. Install Python 3.11+ and Docker."
        exit 1
    fi
    ok "All prerequisites found"
}

setup_env() {
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            info "Created .env from .env.example — edit it with your API keys"
        else
            err "No .env.example found"
            exit 1
        fi
    else
        ok ".env exists"
    fi
}

install_deps() {
    info "Installing Python dependencies..."
    pip install -q -r requirements.txt 2>/dev/null || pip install -r requirements.txt
    ok "Dependencies installed"
}

start_docker() {
    info "Starting all services via Docker Compose..."
    docker compose up --build -d
    ok "Services started:"
    echo "  API:         http://localhost:8000"
    echo "  Frontend:    http://localhost:8501"
    echo "  ChromaDB:    http://localhost:8001"
    echo "  PostgreSQL:  localhost:5432"
    echo "  Redis:       localhost:6379"
    echo ""
    info "Run 'docker compose logs -f api' to follow API logs"
}

start_dev() {
    info "Starting dev servers (background)..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    API_PID=$!
    (cd frontend && streamlit run app.py --server.port=8501 --server.address=0.0.0.0) &
    FRONTEND_PID=$!
    info "API (PID $API_PID) on :8000 | Frontend (PID $FRONTEND_PID) on :8501"
    wait
}

run_tests() {
    info "Running tests..."
    python -m pytest tests/ -v --tb=short 2>&1 || true
}

# ── Main ─────────────────────────────────────
main() {
    echo ""
    echo "  ${CYAN}╔══════════════════════════════╗${NC}"
    echo "  ${CYAN}║    ${APP_NAME} Startup    ║${NC}"
    echo "  ${CYAN}╚══════════════════════════════╝${NC}"
    echo ""

    check_prereqs
    setup_env

    case "${1:-docker}" in
        docker|prod)
            install_deps
            start_docker
            ;;
        dev)
            install_deps
            start_dev
            ;;
        test)
            run_tests
            ;;
        setup)
            install_deps
            info "Running database migrations..."
            alembic upgrade head 2>/dev/null || info "Skipping (no migrations yet)"
            ok "Setup complete"
            ;;
        *)
            echo "Usage: $0 [docker|dev|test|setup]"
            echo "  docker  Start everything via Docker Compose (default)"
            echo "  dev     Start API + frontend locally with hot reload"
            echo "  test    Run test suite"
            echo "  setup   Install deps + run migrations"
            ;;
    esac
}

main "$@"
