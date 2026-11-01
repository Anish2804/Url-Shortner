# Makefile for URL Shortening & Distributed Analytics Platform
ifeq ($(OS),Windows_NT)
    PYTHON := .venv/Scripts/python.exe
    PYTEST := .venv/Scripts/pytest.exe
    UVICORN := .venv/Scripts/uvicorn.exe
    FLAKE8 := .venv/Scripts/flake8.exe
else
    PYTHON := .venv/bin/python
    PYTEST := .venv/bin/pytest
    UVICORN := .venv/bin/uvicorn
    FLAKE8 := .venv/bin/flake8
endif

.PHONY: help dev worker rollup test coverage lint benchmark lock

help:
	@echo "Available make commands:"
	@echo "  make dev        - Run FastAPI application with auto-reload"
	@echo "  make worker     - Run background Kafka consumer worker"
	@echo "  make rollup     - Run daily analytics aggregation cron"
	@echo "  make test       - Execute test suite"
	@echo "  make coverage   - Run test suite with branch coverage"
	@echo "  make lint       - Run flake8 code analysis"
	@echo "  make benchmark  - Run latency/RPS performance benchmark"
	@echo "  make lock       - Freeze current environment to requirements.lock"

dev:
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	$(PYTHON) -m app.workers.analytics_worker

rollup:
	$(PYTHON) -m app.workers.aggregation_cron

test:
	$(PYTEST) -v tests/

coverage:
	$(PYTEST) --cov=app --cov-report=term-missing --cov-report=html tests/

lint:
	$(FLAKE8) app --max-line-length=120

benchmark:
	$(PYTHON) tests/performance/benchmark_runner.py --url http://localhost:8000 -c 20 -n 1000 --paths /health /metrics

lock:
	$(PYTHON) -m pip freeze > requirements.lock
