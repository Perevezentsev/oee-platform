# Удобные команды для разработки
# Использование: make up, make migrate, make shell и т.д.

.PHONY: up down logs shell migrate migration ps

# Запустить все сервисы
up:
	docker compose up -d

# Остановить
down:
	docker compose down

# Логи backend в реальном времени
logs:
	docker compose logs -f backend

# Bash внутри контейнера backend
shell:
	docker compose exec backend bash

# Применить все миграции
migrate:
	docker compose exec backend alembic upgrade head

# Создать новую миграцию (make migration msg="add something")
migration:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

# Откатить последнюю миграцию
rollback:
	docker compose exec backend alembic downgrade -1

# Статус сервисов
ps:
	docker compose ps

# Подключиться к psql
psql:
	docker compose exec postgres psql -U oee_user -d oee_db
