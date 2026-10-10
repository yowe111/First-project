"""
note.py — СХЕМЫ ЗАМЕТОК.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    """Тело запроса на создание.

    `owner_id` здесь намеренно отсутствует: владельца сервер берёт из
    токена. Если бы клиент присылал его сам, можно было бы создать
    заметку от чужого имени.
    """

    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)


class NoteUpdate(BaseModel):
    """Частичное обновление."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1)


class NoteRead(BaseModel):
    id: int
    title: str
    body: str
    owner_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
