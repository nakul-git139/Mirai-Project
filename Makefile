.PHONY: dev test test-e2e test-live clean seed setup-backend setup-frontend help

PYTHON ?= python3.11
VENV = backend/venv
BIN = $(VENV)/bin

help:
	@echo "Available commands:"
	@echo "  make dev       - Bootstrap dependencies if needed and launch backend + frontend"
	@echo "  make test      - Run fast offline backend unit & integration tests"
	@echo "  make test-e2e  - Run Playwright browser flow with isolated test database"
	@echo "  make test-live - Run live remote Ollama tests (http://10.134.74.60:11434)"
	@echo "  make seed      - Seed database with admin, demo student, and 5 sample profiles"
	@echo "  make clean     - Wipe virtual environment, node_modules, and local database"

dev: setup-backend setup-frontend
	@echo "=========================================================="
	@echo " Starting Placement Readiness Copilot"
	@echo " Backend:  http://localhost:8000 (Docs: http://localhost:8000/docs)"
	@echo " Frontend: http://localhost:5173"
	@echo "=========================================================="
	@trap 'kill 0' EXIT; \
	$(BIN)/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir backend & \
	(cd frontend && npm run dev -- --host 0.0.0.0 --port 5173)

test: setup-backend
	@echo "Running fast offline backend tests with pytest..."
	$(BIN)/pytest -v

test-e2e: setup-backend setup-frontend
	@echo "Starting isolated E2E Playwright test runner..."
	@bash scripts/run_e2e.sh

test-live: setup-backend
	@echo "Running live remote Ollama tests with pytest against http://10.134.74.60:11434..."
	$(BIN)/pytest -m live -v -o addopts=""

seed: setup-backend
	@echo "Seeding database with admin, demo student, and 5 sample student profiles..."
	PYTHONPATH=backend $(BIN)/python3 backend/scripts/seed_data.py

setup-backend:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating Python virtualenv in $(VENV) with $(PYTHON)..."; \
		$(PYTHON) -m venv $(VENV); \
		$(BIN)/pip install --upgrade pip; \
		$(BIN)/pip install -r backend/requirements.txt; \
		echo "Installing Playwright chromium browser..."; \
		$(BIN)/playwright install chromium; \
	fi

setup-frontend:
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "Installing frontend dependencies..."; \
		(cd frontend && npm install); \
	fi

clean:
	@echo "Removing venv, node_modules, build artifacts, and databases..."
	rm -rf $(VENV) backend/venv_py311
	rm -rf frontend/node_modules frontend/dist
	rm -rf backend/data/*.db backend/data/*.json backend/data/uploads/*
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean completed."
