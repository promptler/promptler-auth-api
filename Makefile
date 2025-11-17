.PHONY: help install dev migrate upgrade downgrade test clean run docker-up docker-down

help:
	@echo "Promptler Auth API - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install      Install dependencies"
	@echo "  make dev          Set up development environment"
	@echo ""
	@echo "Database:"
	@echo "  make migrate      Create a new database migration"
	@echo "  make upgrade      Run database migrations"
	@echo "  make downgrade    Rollback last migration"
	@echo ""
	@echo "Development:"
	@echo "  make run          Run development server"
	@echo "  make docker-up    Start PostgreSQL with Docker"
	@echo "  make docker-down  Stop PostgreSQL Docker container"
	@echo ""
	@echo "Maintenance:"
	@echo "  make test         Run tests (when implemented)"
	@echo "  make clean        Clean up generated files"
	@echo ""

install:
	pip install -r requirements.txt

dev: install
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.example..."; \
		cp .env.example .env; \
		echo "Please edit .env with your configuration"; \
	fi
	@echo "Run 'make docker-up' to start PostgreSQL"
	@echo "Then run 'make upgrade' to create database schema"
	@echo "Finally, run 'make run' to start the server"

migrate:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

upgrade:
	alembic upgrade head

downgrade:
	alembic downgrade -1

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-up:
	docker-compose up -d
	@echo "PostgreSQL is starting..."
	@echo "Connection string: postgresql://promptler:promptler@localhost:5432/promptler_auth"

docker-down:
	docker-compose down

test:
	@echo "Tests not yet implemented"
	# pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
