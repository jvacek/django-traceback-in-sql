.PHONY: help build up down clean shell test

help:
	@echo "Django SQL PythonStack - Testing Commands"
	@echo ""
	@echo "Docker Management:"
	@echo "  make build             - Build the test container image"
	@echo "  make up                - Start database containers"
	@echo "  make down              - Stop all containers"
	@echo "  make clean             - Remove all containers and volumes"
	@echo ""
	@echo "Testing:"
	@echo "  make test              - Run tests (pass TOX_ENV to specify environments)"
	@echo ""
	@echo "Examples:"
	@echo "  make test                                    # Run all 21 environments"
	@echo "  make test TOX_ENV=py312-django52-sqlite     # Single environment"
	@echo "  make test TOX_ENV=py312-django52-postgres   # Python 3.12 + Django 5.2 + Postgres"
	@echo "  make test TOX_ENV=py310-django42-mysql      # Python 3.10 + Django 4.2 + MySQL"
	@echo ""
	@echo "Multiple environments:"
	@echo "  make test TOX_ENV=\"py312-django52-sqlite,py313-django52-mysql\""
	@echo ""
	@echo "By Django version:"
	@echo "  make test TOX_ENV=\"py{310,311,312}-django42-{sqlite,postgres,mysql}\""
	@echo "  make test TOX_ENV=\"py{310,311,312,313}-django52-{sqlite,postgres,mysql}\""
	@echo ""
	@echo "Debugging:"
	@echo "  make shell             - Open shell in test container"
	@echo "  docker-compose run --rm test tox list       # List all environments"

build:
	@echo "Building test container with UV and all database drivers..."
	docker-compose build test

up:
	@echo "Starting database containers..."
	docker-compose up -d postgres mysql
	@echo "Waiting for databases to be ready..."
	@sleep 5

down:
	@echo "Stopping containers..."
	docker-compose down

clean:
	@echo "Cleaning up all containers and volumes..."
	docker-compose down -v
	@echo "Done!"

shell: up
	@echo "Opening shell in test container..."
	@echo "All database drivers and Python versions are available."
	@echo "Example: tox -e py312-django52-postgres"
	docker-compose run --rm test /bin/bash

test: up
	@if [ -z "$(TOX_ENV)" ]; then \
		echo "Running all tests..."; \
		docker-compose run --rm -e DB_HOST=postgres test tox -e "py{310,311,312}-django{42,52}-{sqlite,postgres}"; \
		docker-compose run --rm -e DB_HOST=mysql test tox -e "py{310,311,312}-django42-mysql,py{310,311,312,313}-django52-mysql"; \
	else \
		echo "Running tox -e $(TOX_ENV)"; \
		if echo "$(TOX_ENV)" | grep -q "mysql"; then \
			docker-compose run --rm -e DB_HOST=mysql test tox -e "$(TOX_ENV)"; \
		else \
			docker-compose run --rm -e DB_HOST=postgres test tox -e "$(TOX_ENV)"; \
		fi; \
	fi
