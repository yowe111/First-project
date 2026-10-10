# Makefile — короткие команды-ярлыки для частых действий.
# Запускаются так: `make up`, `make logs` и т.д.
# (На Windows для работы make может понадобиться установить его отдельно,
#  либо просто копируйте команды справа и запускайте их вручную.)

include .env

# Собрать образы и запустить все контейнеры.
up:
	docker compose up --build

# Запустить в фоне (detached).
upd:
	docker compose up --build -d

# Остановить и удалить контейнеры.
down:
	docker compose down

# Показать логи приложения в реальном времени.
logs:
	docker compose logs -f app

# Показать статус контейнеров.
ps:
	docker compose ps -a

# Перезапустить контейнеры.
restart:
	docker compose restart

# Зайти внутрь базы данных через psql.
db:
	docker compose exec -it postgres psql -U $(DB_USER) -d $(DB_NAME)

# Накатить миграции вручную (обычно это уже делает docker compose up).
migrateup:
	docker compose exec -it app alembic upgrade head

# Создать новую миграцию по изменениям моделей (autogenerate).
migrate:
	docker compose exec -it app alembic revision --autogenerate -m "change"

# Запустить тесты внутри контейнера приложения.
test:
	docker compose exec -it app pytest -q

# Запустить тесты локально, без Docker. Выполняется из папки backend:
# там лежат pyproject.toml с настройками pytest и сам код.
test-local:
	cd backend && pytest -q

# Поднять Jupyter для ноутбуков (нужны зависимости из группы notebooks).
lab:
	jupyter lab notebooks
