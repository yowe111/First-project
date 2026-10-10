"""
config.py — НАСТРОЙКИ ПРИЛОЖЕНИЯ.

Любой программе нужны параметры: адрес базы данных, секретные ключи, сроки
жизни токенов. Держать их прямо в коде плохо — это и небезопасно, и неудобно
менять. Поэтому они лежат в файле `.env`, а этот модуль их оттуда читает.

Библиотека pydantic-settings берёт значения из переменных окружения
(их задаёт docker-compose из `.env`) и складывает в объект `settings`.
Дальше по всему проекту пишем `settings.secret_key`.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Все параметры приложения в одном месте."""

    # ── Приложение ────────────────────────────────────────────────────
    app_name: str = "My API"
    app_version: str = "0.4.0"
    debug: bool = False

    # ── База данных ───────────────────────────────────────────────────
    # Строка подключения (DSN). Значения по умолчанию нет — его
    # обязательно нужно задать в .env, иначе приложение не стартует.
    postgres_dsn: str

    # ── Токены ────────────────────────────────────────────────────────
    secret_key: str = "super-secret-key-change-me"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Лишние переменные из .env игнорируем: например, POSTGRES_USER
        # нужен docker-compose, но не коду приложения.
        extra="ignore",
    )


# Один объект настроек на всё приложение: читается один раз при импорте.
settings = Settings()
