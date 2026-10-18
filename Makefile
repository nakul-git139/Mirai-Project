.PHONY: dev test clean seed setup-backend setup-frontend help

PYTHON ?= python3
VENV = backend/venv
BIN = $(VENV)/bin

help:
	@echo "Available commands:"
	@echo "  make dev    - Bootstrap dependencies if needed and launch backend + frontend"
	@echo "  make test   - Run all backend unit & integration tests"
	@echo "  make seed   - Seed database with admin, demo student, and 5 sample profiles"
	@echo "  make clean  - Wipe virtual environment, node_modules, and local database"

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
	@echo "Running all backend tests with pytest..."
	$(BIN)/pytest -v

seed: setup-backend
	@echo "Seeding database with admin, demo student, and 5 sample student profiles..."
	PYTHONPATH=backend $(BIN)/python3 backend/scripts/seed_data.py

setup-backend:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating Python virtualenv in $(VENV)..."; \
		$(PYTHON) -m venv $(VENV); \
		$(BIN)/pip install --upgrade pip; \
		$(BIN)/pip install -r backend/requirements.txt; \
	fi

setup-frontend:
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "Installing frontend dependencies..."; \
		(cd frontend && npm install); \
	fi

clean:
	@echo "Removing venv, node_modules, build artifacts, and databases..."
	rm -rf $(VENV)
	rm -rf frontend/node_modules frontend/dist
	rm -rf backend/data/*.db backend/data/*.json backend/data/uploads/*
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean completed."
