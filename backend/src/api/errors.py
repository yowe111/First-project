"""
errors.py — ПЕРЕВОД ДОМЕННЫХ ОШИБОК В HTTP-ОТВЕТЫ.

Сервисы бросают `AppError` и его наследников — исключения на языке
предметной области. Здесь, в единственном месте приложения, они
превращаются в ответ с нужным кодом.

Что это даёт:

- формат ошибки одинаковый во всём API: всегда `{"detail": "..."}`;
- сервисы не зависят от FastAPI и переиспользуются где угодно;
- чтобы поменять формат ошибок для всего продукта, правится один файл.

Формат совпадает с тем, что FastAPI возвращает для `HTTPException`,
поэтому клиенту всё равно, кто именно сформировал ответ.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.exceptions import AppError


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Превратить ошибку предметной области в JSON-ответ."""
    assert isinstance(exc, AppError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        # Для 401 сюда попадёт WWW-Authenticate: Bearer — этого требует
        # стандарт, и по нему клиенты понимают, что нужно залогиниться.
        headers=exc.headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Подключить обработчики к приложению.

    Регистрируем только базовый класс: наследники ловятся автоматически,
    потому что каждый из них — это `AppError`.
    """
    app.add_exception_handler(AppError, app_error_handler)
