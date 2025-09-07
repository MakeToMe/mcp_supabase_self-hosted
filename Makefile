# Makefile for Supabase MCP Server

.PHONY: help install dev test lint format clean build run docker-build docker-run

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	poetry install

dev: ## Install development dependencies
	poetry install --with dev
	poetry run pre-commit install

test: ## Run tests
	poetry run pytest -v --cov=src --cov-report=term-missing

test-watch: ## Run tests in watch mode
	poetry run pytest-watch

lint: ## Run linting
	poetry run flake8 src tests
	poetry run mypy src

format: ## Format code
	poetry run black src tests
	poetry run isort src tests

clean: ## Clean up build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build: ## Build the package
	poetry build

run: ## Run the development server
	poetry run python -m supabase_mcp_server.main

docker-build: ## Build Docker image
	docker build -t supabase-mcp-server .

docker-run: ## Run Docker container
	docker-compose up -d

docker-stop: ## Stop Docker container
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

setup-env: ## Setup environment file
	cp .env.example .env
	@echo "Please edit .env with your configuration"

check: lint test ## Run all checks

ci: install check ## Run CI pipeline