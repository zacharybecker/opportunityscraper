.PHONY: up down build logs backend-logs frontend-logs db-logs shell migrate revision

COMPOSE = docker compose -f docker/docker-compose.yml --env-file docker/.env

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

backend-logs:
	$(COMPOSE) logs -f backend

frontend-logs:
	$(COMPOSE) logs -f frontend

db-logs:
	$(COMPOSE) logs -f postgres

shell:
	$(COMPOSE) exec backend bash

migrate:
	$(COMPOSE) exec backend alembic upgrade head

revision:
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(msg)"

psql:
	$(COMPOSE) exec postgres psql -U oppscraper

restart:
	$(COMPOSE) restart backend

clean:
	$(COMPOSE) down -v
