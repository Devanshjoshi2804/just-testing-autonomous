.PHONY: help setup build up down restart logs shell test clean

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)AutoTest-RL Docker Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

setup: ## Initial setup - copy .env.template to .env
	@echo "$(BLUE)Setting up environment...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.template .env; \
		echo "$(GREEN)✓ Created .env file. Please edit it with your API keys.$(NC)"; \
	else \
		echo "$(YELLOW)⚠ .env file already exists.$(NC)"; \
	fi

build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build

up: ## Start all services
	@echo "$(BLUE)Starting services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started!$(NC)"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo "Flower: http://localhost:5555"

up-build: ## Build and start all services
	@echo "$(BLUE)Building and starting services...$(NC)"
	docker-compose up -d --build
	@echo "$(GREEN)✓ Services started!$(NC)"

down: ## Stop and remove containers
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped!$(NC)"

restart: ## Restart all services
	@echo "$(BLUE)Restarting services...$(NC)"
	docker-compose restart
	@echo "$(GREEN)✓ Services restarted!$(NC)"

logs: ## View logs (follow mode)
	docker-compose logs -f

logs-api: ## View API logs
	docker-compose logs -f api

logs-worker: ## View Celery worker logs
	docker-compose logs -f celery_worker

ps: ## Show running services
	docker-compose ps

shell: ## Open bash shell in API container
	docker-compose exec api bash

python: ## Open Python shell in API container
	docker-compose exec api python

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	docker-compose exec api pytest tests/ -v

test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	docker-compose exec api pytest tests/ --cov=src --cov-report=html
	@echo "$(GREEN)✓ Coverage report: htmlcov/index.html$(NC)"

health: ## Check service health
	@echo "$(BLUE)Checking service health...$(NC)"
	@curl -f http://localhost:8000/health && echo "$(GREEN)✓ API is healthy$(NC)" || echo "$(YELLOW)⚠ API is not responding$(NC)"
	@curl -f http://localhost:8001/api/v1/heartbeat && echo "$(GREEN)✓ ChromaDB is healthy$(NC)" || echo "$(YELLOW)⚠ ChromaDB is not responding$(NC)"
	@redis-cli -h localhost -p 6379 ping > /dev/null && echo "$(GREEN)✓ Redis is healthy$(NC)" || echo "$(YELLOW)⚠ Redis is not responding$(NC)"

clean: ## Remove containers and volumes (⚠️ deletes data)
	@echo "$(YELLOW)⚠️  This will delete all data. Are you sure? [y/N]$(NC)" && read ans && [ $${ans:-N} = y ]
	docker-compose down -v
	@echo "$(GREEN)✓ Cleaned up!$(NC)"

clean-all: ## Remove containers, volumes, and images (⚠️ deletes everything)
	@echo "$(YELLOW)⚠️  This will delete EVERYTHING. Are you sure? [y/N]$(NC)" && read ans && [ $${ans:-N} = y ]
	docker-compose down -v --rmi all
	docker system prune -f
	@echo "$(GREEN)✓ Deep cleaned!$(NC)"

rebuild: ## Full rebuild (stop, clean build cache, build, start)
	@echo "$(BLUE)Full rebuild...$(NC)"
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "$(GREEN)✓ Rebuild complete!$(NC)"

scale-workers: ## Scale celery workers (usage: make scale-workers N=4)
	@if [ -z "$(N)" ]; then \
		echo "$(YELLOW)Usage: make scale-workers N=4$(NC)"; \
	else \
		docker-compose up -d --scale celery_worker=$(N); \
		echo "$(GREEN)✓ Scaled to $(N) workers$(NC)"; \
	fi

train-rl: ## Start RL training service
	@echo "$(BLUE)Starting RL training...$(NC)"
	docker-compose --profile training up rl_trainer

backup-db: ## Backup ChromaDB data
	@echo "$(BLUE)Backing up ChromaDB...$(NC)"
	@mkdir -p backups
	@docker-compose exec chromadb tar -czf /tmp/chroma-backup-$$(date +%Y%m%d-%H%M%S).tar.gz /chroma/chroma
	@docker cp autotest-chromadb:/tmp/chroma-backup-$$(date +%Y%m%d-%H%M%S).tar.gz ./backups/
	@echo "$(GREEN)✓ Backup created in ./backups/$(NC)"

dev: setup up-build logs-api ## Full dev setup (setup → build → start → logs)

prod: ## Production deployment
	@echo "$(BLUE)Starting in production mode...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)⚠ Please create .env file first (make setup)$(NC)"; \
		exit 1; \
	fi
	docker-compose -f docker-compose.yml up -d --build
	@echo "$(GREEN)✓ Production services started!$(NC)"

docs: ## Open API documentation in browser
	@echo "$(BLUE)Opening API docs...$(NC)"
	@open http://localhost:8000/docs 2>/dev/null || xdg-open http://localhost:8000/docs 2>/dev/null || echo "Open http://localhost:8000/docs in your browser"

flower: ## Open Flower dashboard in browser
	@echo "$(BLUE)Opening Flower dashboard...$(NC)"
	@open http://localhost:5555 2>/dev/null || xdg-open http://localhost:5555 2>/dev/null || echo "Open http://localhost:5555 in your browser"

stats: ## Show Docker resource usage
	docker stats --no-stream
