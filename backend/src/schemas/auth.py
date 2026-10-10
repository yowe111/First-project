"""
auth.py — СХЕМЫ АВТОРИЗАЦИИ.
"""

from pydantic import BaseModel


class Token(BaseModel):
    """Ответ на успешный вход.

    Поля названы так не случайно: `access_token` и `token_type` — часть
    стандарта OAuth2. Благодаря этому кнопка Authorize в `/docs` и
    готовые клиентские библиотеки понимают ответ без настройки.
    """

    access_token: str
    token_type: str = "bearer"
