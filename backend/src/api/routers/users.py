"""
users.py — ПРОФИЛЬ, СПИСОК, РОЛИ, БЛОКИРОВКИ.

Порядок маршрутов важен: `/me` объявлен раньше `/{user_id}`, иначе FastAPI
решит, что «me» — это значение параметра `user_id`, и попытается найти
пользователя с таким номером.
"""

from fastapi import APIRouter, Query

from src.api.deps import (
    CurrentAdmin,
    CurrentUser,
    PaginationDep,
    UserServiceDep,
)
from src.schemas.common import Message, Page
from src.schemas.user import PasswordChange, RoleUpdate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.get("/me", response_model=UserRead, summary="Мой профиль")
async def read_me(current_user: CurrentUser):
    """Данные того, чей токен прислан. Запрос в базу уже сделала зависимость."""
    return current_user


@router.patch("/me", response_model=UserRead, summary="Изменить свой профиль")
async def update_me(
    data: UserUpdate,
    current_user: CurrentUser,
    users: UserServiceDep,
):
    """Частичное обновление. Пароль и роль сюда не входят."""
    return await users.update_profile(current_user, data)


@router.post("/me/password", response_model=Message, summary="Сменить пароль")
async def change_password(
    data: PasswordChange,
    current_user: CurrentUser,
    users: UserServiceDep,
):
    """Новый пароль в ответе не возвращаем — ему там не место."""
    await users.change_password(current_user, data)
    return Message(detail="Пароль обновлён")


@router.get("", response_model=Page[UserRead], summary="Список пользователей")
async def list_users(
    current_user: CurrentUser,
    users: UserServiceDep,
    pagination: PaginationDep,
    q: str | None = Query(
        default=None,
        description="Поиск по логину или почте, без учёта регистра",
    ),
):
    """Нужен токен, роль любая."""
    items, total = await users.search(
        query=q,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page[UserRead](
        items=items,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.post(
    "/{user_id}/block",
    response_model=UserRead,
    summary="Заблокировать пользователя",
)
async def block_user(user_id: int, admin: CurrentAdmin, users: UserServiceDep):
    """Себя блокировать нельзя."""
    return await users.block(admin, user_id)


@router.post(
    "/{user_id}/unblock",
    response_model=UserRead,
    summary="Снять блокировку",
)
async def unblock_user(user_id: int, admin: CurrentAdmin, users: UserServiceDep):
    """После разблокировки человек снова может войти."""
    return await users.unblock(user_id)


@router.patch(
    "/{user_id}/role",
    response_model=UserRead,
    summary="Сменить роль",
)
async def update_user_role(
    user_id: int,
    data: RoleUpdate,
    admin: CurrentAdmin,
    users: UserServiceDep,
):
    """Себе роль менять нельзя, иначе можно остаться без администратора."""
    return await users.change_role(admin, user_id, data.role)
