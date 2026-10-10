"""
notes.py — ЗАМЕТКИ ПОЛЬЗОВАТЕЛЯ.

Правила доступа («чужую не показываем», «править можно только свою»)
живут в `src/services/note.py`. Здесь остались только адреса, коды ответов
и описания для документации.
"""

from fastapi import APIRouter, Query, status

from src.api.deps import CurrentUser, NoteServiceDep, PaginationDep
from src.schemas.common import Page
from src.schemas.note import NoteCreate, NoteRead, NoteUpdate

router = APIRouter(prefix="/notes", tags=["Заметки"])


@router.post(
    "",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать заметку",
)
async def create_note(
    data: NoteCreate,
    current_user: CurrentUser,
    notes: NoteServiceDep,
):
    """Владельца берём из токена — клиент его не присылает."""
    return await notes.create(current_user, data)


@router.get("", response_model=Page[NoteRead], summary="Список заметок")
async def list_notes(
    current_user: CurrentUser,
    notes: NoteServiceDep,
    pagination: PaginationDep,
    show_all: bool = Query(
        default=False,
        alias="all",
        description="Только для admin: показать заметки всех пользователей",
    ),
):
    """По умолчанию только свои. `?all=true` — все, если ты администратор."""
    items, total = await notes.list_for(
        current_user,
        limit=pagination.limit,
        offset=pagination.offset,
        show_all=show_all,
    )
    return Page[NoteRead](
        items=items,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get("/{note_id}", response_model=NoteRead, summary="Одна заметка")
async def read_note(
    note_id: int,
    current_user: CurrentUser,
    notes: NoteServiceDep,
):
    """Чужую обычный пользователь не увидит — 404, а не 403."""
    return await notes.get_visible(current_user, note_id)


@router.patch("/{note_id}", response_model=NoteRead, summary="Изменить заметку")
async def update_note(
    note_id: int,
    data: NoteUpdate,
    current_user: CurrentUser,
    notes: NoteServiceDep,
):
    """Править можно только свою, даже администратору."""
    return await notes.update(current_user, note_id, data)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить заметку",
)
async def delete_note(
    note_id: int,
    current_user: CurrentUser,
    notes: NoteServiceDep,
):
    """Свою — всегда. Чужую — только администратор, это модерация."""
    await notes.delete(current_user, note_id)
