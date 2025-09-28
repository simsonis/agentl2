COMPOSE ?= docker compose

.PHONY: up down init-db laws prec logs

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down -v

init-db:
	bash scripts/init_db.sh

laws:
	$(COMPOSE) exec collector poetry run agentl2-collect-laws $(ARGS)

prec:
	$(COMPOSE) exec collector poetry run agentl2-collect-prec $(ARGS)

logs:
	$(COMPOSE) logs -f
