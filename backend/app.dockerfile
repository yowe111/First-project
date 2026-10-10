# Базовый образ: лёгкая версия Python 3.11.
FROM python:3.11-slim

# Отключаем создание .pyc файлов и включаем небуферизованный вывод логов.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Рабочая директория внутри контейнера. Все команды ниже выполняются отсюда.
WORKDIR /app

# Устанавливаем Poetry — менеджер зависимостей.
RUN pip install --no-cache-dir poetry

# Сначала копируем ТОЛЬКО файл с зависимостями.
# Так Docker сможет закешировать шаг установки и не переустанавливать
# библиотеки каждый раз, когда мы меняем код приложения.
COPY pyproject.toml ./

# Говорим Poetry ставить пакеты прямо в систему (без отдельного venv),
# генерируем lock-файл и устанавливаем зависимости основной группы.
RUN poetry config virtualenvs.create false \
    && poetry lock \
    && poetry install --no-root

# Теперь копируем весь остальной код проекта.
COPY . .

# Команда по умолчанию: запуск веб-сервера uvicorn.
# (В docker-compose.yaml она переопределяется, чтобы добавить --reload.)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
