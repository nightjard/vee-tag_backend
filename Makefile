.PHONY: help build up down restart logs clean test init-data

help: ## Показать справку
	@echo "Pozily Backend - Команды:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Собрать Docker образы
	docker-compose build

up: ## Запустить все сервисы
	docker-compose up -d
	@echo ""
	@echo "Сервисы запущены!"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo "Health: http://localhost:8000/health"

up-logs: ## Запустить с логами
	docker-compose up

down: ## Остановить все сервисы
	docker-compose down

restart: down up ## Перезапустить все сервисы

logs: ## Показать логи
	docker-compose logs -f

logs-app: ## Логи приложения
	docker-compose logs -f app

logs-db: ## Логи базы данных
	docker-compose logs -f db

clean: ## Очистить всё (включая данные БД)
	docker-compose down -v
	@echo "Все данные удалены!"

test: ## Запустить тестовый скрипт
	@echo "Запуск тестов API..."
	python3 test_api.py

init-data: ## Инициализировать тестовые данные
	@echo "Инициализация тестовых данных..."
	docker-compose exec app python init_test_data.py

shell-app: ## Войти в контейнер приложения
	docker-compose exec app /bin/bash

shell-db: ## Войти в PostgreSQL
	docker-compose exec db psql -U pozily_user -d pozily_db

status: ## Статус сервисов
	docker-compose ps

install: build up ## Полная установка
	@echo ""
	@echo "Установка завершена!"
	@echo ""
	@echo "Следующие шаги:"
	@echo "1. Инициализируйте тестовые данные: make init-data"
	@echo "2. Запустите тесты: make test"
	@echo "3. Откройте документацию: http://localhost:8000/docs"
