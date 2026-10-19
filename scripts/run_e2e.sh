#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

VENV="backend/venv"
BIN="$VENV/bin"
TEST_DB_FILE="$PROJECT_ROOT/backend/data/test_e2e.db"
TEST_DB_URL="sqlite:///$TEST_DB_FILE"

# Clean up any leftover test database
rm -f "$TEST_DB_FILE"*

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "Shutting down test servers..."
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    # Also terminate any processes listening on port 8000 or 5173 spawned by subshells
    sleep 0.5
    lsof -ti :8000 | xargs kill -9 2>/dev/null || true
    lsof -ti :5173 | xargs kill -9 2>/dev/null || true
    # Clean up isolated temporary database
    rm -f "$TEST_DB_FILE"*
    echo "Isolated test database wiped ($TEST_DB_FILE*)."
}

trap cleanup EXIT INT TERM

echo "=========================================================="
echo " Starting Isolated E2E Playwright Flow"
echo " Temporary Test Database: $TEST_DB_FILE"
echo "=========================================================="

BACKEND_LOG="$PROJECT_ROOT/backend/data/uvicorn_e2e.log"
FRONTEND_LOG="$PROJECT_ROOT/backend/data/vite_e2e.log"
rm -f "$BACKEND_LOG" "$FRONTEND_LOG"

# 1. Start backend with isolated database
export DATABASE_URL="$TEST_DB_URL"
"$BIN/uvicorn" app.main:app --host 127.0.0.1 --port 8000 --app-dir backend > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# 2. Start frontend
(cd frontend && npm run dev -- --host 127.0.0.1 --port 5173 > "$FRONTEND_LOG" 2>&1) &
FRONTEND_PID=$!

echo "Waiting for backend on http://127.0.0.1:8000/api/health..."
for i in {1..40}; do
    if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
        echo "Backend is ready."
        break
    fi
    sleep 0.5
    if [ "$i" -eq 40 ]; then
        echo "ERROR: Backend failed to start within 20 seconds. Server log:"
        cat "$BACKEND_LOG"
        exit 1
    fi
done

echo "Waiting for frontend on http://127.0.0.1:5173..."
for i in {1..40}; do
    if curl -s http://127.0.0.1:5173 > /dev/null 2>&1; then
        echo "Frontend is ready."
        break
    fi
    sleep 0.5
    if [ "$i" -eq 40 ]; then
        echo "ERROR: Frontend failed to start within 20 seconds. Server log:"
        cat "$FRONTEND_LOG"
        exit 1
    fi
done

echo "Running Playwright browser flow..."
export DATABASE_URL="$TEST_DB_URL"
"$BIN/pytest" backend/tests/test_browser_tracker_flow.py -v -s -o addopts=""
EXIT_CODE=$?

exit $EXIT_CODE
