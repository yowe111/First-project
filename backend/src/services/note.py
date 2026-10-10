"""
note.py — ЗАМЕТКИ И ПРАВА НА НИХ.

Весь свод правил доступа собран в одном месте — в методах `_can_*`.
Это важнее, чем кажется: пока проверки раскиданы по обработчикам, рано или
поздно в одном из них забудут условие, и чужая запись станет видна.
"""

from src.core.exceptions import NotFoundError, PermissionDeniedError
from src.enums import UserRole
from src.models.note import Note
from src.models.user import User
from src.repositories.note import NoteRepository
from src.schemas.note import NoteCreate, NoteUpdate

# Текст один на все случаи: о существовании чужой заметки не сообщаем
# ни кодом ответа, ни формулировкой.
_NOT_FOUND = "Заметка не найдена"


class NoteService:
    def __init__(self, notes: NoteRepository) -> None:
        self.notes = notes

    # ── Правила доступа ───────────────────────────────────────────────

    @staticmethod
    def _can_see(note: Note, user: User) -> bool:
        return note.owner_id == user.id or user.role == UserRole.ADMIN

    @staticmethod
    def _can_edit(note: Note, user: User) -> bool:
        """Править можно только свою — даже администратору.

        Модерация означает «удалить», а не «переписать чужой текст».
        """
        return note.owner_id == user.id

    @staticmethod
    def _can_delete(note: Note, user: User) -> bool:
        return note.owner_id == user.id or user.role == UserRole.ADMIN

    # ── Операции ──────────────────────────────────────────────────────

    async def create(self, owner: User, data: NoteCreate) -> Note:
        note = self.notes.create(
            title=data.title,
            body=data.body,
            owner_id=owner.id,
        )
        return await self.notes.save(note)

    async def list_for(
        self,
        user: User,
        *,
        limit: int,
        offset: int,
        show_all: bool = False,
    ) -> tuple[list[Note], int]:
        """Список заметок: по умолчанию свои, с флагом — все (для админа).

        Здесь 403, а не 404: человек просит заведомо административный
        режим, и честно сказать «тебе нельзя» безопасно — никакой
        информации о чужих записях это не раскрывает.
        """
        if show_all:
            if user.role != UserRole.ADMIN:
                raise PermissionDeniedError(
                    "Только администратор может смотреть все заметки"
                )
            return await self.notes.paginate_all(limit=limit, offset=offset)

        return await self.notes.paginate_for_owner(
            user.id,
            limit=limit,
            offset=offset,
        )

    async def get_visible(self, user: User, note_id: int) -> Note:
        note = await self.notes.get_by_id(note_id)
        if note is None or not self._can_see(note, user):
            raise NotFoundError(_NOT_FOUND)
        return note

    async def update(self, user: User, note_id: int, data: NoteUpdate) -> Note:
        note = await self.get_visible(user, note_id)
        if not self._can_edit(note, user):
            raise NotFoundError(_NOT_FOUND)

        # Частичное обновление: присланы только те поля, что нужно менять.
        if data.title is not None:
            note.title = data.title
        if data.body is not None:
            note.body = data.body

        return await self.notes.save(note)

    async def delete(self, user: User, note_id: int) -> None:
        note = await self.get_visible(user, note_id)
        if not self._can_delete(note, user):
            raise NotFoundError(_NOT_FOUND)

        await self.notes.delete(note)
        await self.notes.commit()
