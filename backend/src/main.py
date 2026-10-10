"""
main.py — ТОЧКА ВХОДА.

Файл намеренно короткий. Он ничего не считает и ни за что не отвечает —
только собирает приложение из готовых частей:

    настройки  →  обработчики ошибок  →  роутеры  →  служебные страницы

Команда `uvicorn src.main:app` означает «возьми объект `app` из этого файла».

Таблицы в базе создаёт не приложение, а Alembic. В docker-compose команда
выглядит так:

    alembic upgrade head && uvicorn src.main:app ...

сначала накатываются миграции, потом стартует сервер.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from src.api.errors import register_exception_handlers
from src.api.router import api_router
from src.core.config import settings


def create_app() -> FastAPI:
    """Фабрика приложения.

    Почему функция, а не просто `app = FastAPI(...)` на уровне модуля:
    так приложение можно собрать несколько раз с разными настройками —
    например, отдельный экземпляр на каждый тест. Пока это не нужно, но
    переделывать потом дороже, чем написать четыре строки сейчас.
    """
    app = FastAPI(
        title=settings.app_name,
        description="Авторизация, роли, пагинация, заметки",
        version=settings.app_version,
    )

    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/", response_class=HTMLResponse, tags=["Служебное"])
    async def index() -> str:
        """Главная страница: http://localhost:8000/"""
        return """
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="utf-8">
            <title>My API</title>
            <style>
                body { font-family: sans-serif; text-align: center; margin-top: 80px; }
                h1 { font-size: 48px; }
                a { color: #2563eb; }
            </style>
        </head>
        <body>
            <h1>Hello World</h1>
            <p>Это учебное приложение на FastAPI.</p>
            <p>
                Открой <a href="/docs">/docs</a> — там интерактивная документация:
                регистрация, вход, список пользователей и роли.
            </p>
        </body>
        </html>
        """

    @app.get("/hello", tags=["Служебное"])
    async def hello() -> dict[str, str]:
        """Тот же ответ, но в виде JSON."""
        return {"message": "Hello World"}

    @app.get("/health", tags=["Служебное"])
    async def health() -> dict[str, str]:
        """Проверка живости.

        По этому адресу будут стучаться docker healthcheck и внешний
        мониторинг доступности. Он намеренно не ходит в базу: его задача —
        ответить быстро и сказать, что процесс жив.
        """
        return {"status": "ok", "version": settings.app_version}

    return app


app = create_app()
