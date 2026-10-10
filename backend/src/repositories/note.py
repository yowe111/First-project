"""
note.py — ЗАПРОСЫ К ТАБЛИЦЕ `notes`.

Обратите внимание: здесь нет ни слова о том, КОМУ можно видеть заметку.
Репозиторий умеет «дай заметки такого-то владельца» и «дай все» — а решение,
какой из двух вариантов уместен, принимает сервис. Это и есть разделение
«как достать данные» и «кому их можно показать».
"""

from src.models.note import Note
from src.repositories.base import BaseRepository


class NoteRepository(BaseRepository[Note]):
    model = Note
    default_order_by = (Note.id,)

    async def paginate_for_owner(
        self,
        owner_id: int,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Note], int]:
        """Страница заметок одного владельца."""
        return await self.paginate(
            Note.owner_id == owner_id,
            limit=limit,
            offset=offset,
        )

    async def paginate_all(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Note], int]:
        """Страница заметок всех пользователей — для администратора."""
        return await self.paginate(limit=limit, offset=offset)

    async def count_for_owner(self, owner_id: int) -> int:
        return await self.count(Note.owner_id == owner_id)
