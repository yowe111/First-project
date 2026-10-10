"""
common.py — СХЕМЫ, ОБЩИЕ ДЛЯ ВСЕГО API.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Конверт для любого списка с пагинацией.

    Благодаря `Generic[T]` одна схема обслуживает все списки:
    `Page[UserRead]`, `Page[NoteRead]`, позже `Page[DatasetRead]`.
    В `/docs` каждый вариант при этом показан своим типом.

    `total` — сколько записей подошло под фильтр ВСЕГО, а не на этой
    странице. Без этого числа клиент не нарисует постраничную навигацию.
    """

    items: list[T]
    total: int
    limit: int
    offset: int


class Message(BaseModel):
    """Короткий текстовый ответ там, где возвращать объект нечего."""

    detail: str
