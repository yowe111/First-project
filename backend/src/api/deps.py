"""
deps.py — ЗАВИСИМОСТИ FASTAPI (СБОРКА СЛОЁВ).

**Что такое зависимость.** Функция, результат которой FastAPI сам
подставляет в обработчик. Вместо того чтобы в каждом эндпоинте повторять
подготовительный код, мы объявляем «мне нужно вот это».

**Что происходит в этом файле.** Здесь собирается цепочка слоёв:

    сессия  →  репозиторий  →  сервис  →  обработчик

Каждое звено получает предыдущее через `Depends` и не создаёт его само.
Это называется внедрением зависимостей, и польза от него практическая:
в тесте можно подменить любое звено одной строкой
(`app.dependency_overrides[...]`), не трогая код приложения.

**Про сокращения вида `CurrentUser`.** Записи `Annotated[X, Depends(y)]`
длинные, и если писать их в каждом обработчике, сигнатуры станут
нечитаемыми. Поэтому внизу файла объявлены короткие псевдонимы.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.exceptions import PermissionDeniedError
from src.enums import UserRole
from src.models.user import User
from src.repositories.note import NoteRepository
from src.repositories.user import UserRepository
from src.services.auth import AuthService
from src.services.note import NoteService
from src.services.user import UserService

# Схема извлекает токен из заголовка `Authorization: Bearer <токен>`.
# Указанный tokenUrl нужен кнопке Authorize в /docs — она будет логиниться
# именно по этому адресу.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ── Репозитории ───────────────────────────────────────────────────────


def get_user_repository(session: SessionDep) -> UserRepository:
    return UserRepository(session)


def get_note_repository(session: SessionDep) -> NoteRepository:
    return NoteRepository(session)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
NoteRepositoryDep = Annotated[NoteRepository, Depends(get_note_repository)]


# ── Сервисы ───────────────────────────────────────────────────────────


def get_auth_service(users: UserRepositoryDep) -> AuthService:
    return AuthService(users)


def get_user_service(users: UserRepositoryDep) -> UserService:
    return UserService(users)


def get_note_service(notes: NoteRepositoryDep) -> NoteService:
    return NoteService(notes)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
NoteServiceDep = Annotated[NoteService, Depends(get_note_service)]


# ── Текущий пользователь ──────────────────────────────────────────────


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth: AuthServiceDep,
) -> User:
    """Кто прислал запрос. Плохой токен → 401, заблокирован → 403.

    Сама проверка живёт в сервисе; здесь только связывание токена из
    заголовка с бизнес-логикой.
    """
    return await auth.get_user_by_token(token)


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_admin(current_user: CurrentUser) -> User:
    """Разница кодов, которую стоит помнить:

    - 401 Unauthorized — «кто ты?», токена нет или он испорчен;
    - 403 Forbidden — «знаем кто, но тебе сюда нельзя».
    """
    if current_user.role != UserRole.ADMIN:
        raise PermissionDeniedError("Недостаточно прав. Нужна роль администратора.")
    return current_user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]


# ── Пагинация ─────────────────────────────────────────────────────────


@dataclass(slots=True)
class Pagination:
    """Параметры постраничного вывода, общие для всех списков."""

    limit: int
    offset: int


def get_pagination(
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Сколько записей вернуть"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Сколько записей пропустить"),
    ] = 0,
) -> Pagination:
    """Границы заданы здесь один раз.

    Верхний предел важен: без него клиент запросом `?limit=10000000`
    заставит сервер поднять в память всю таблицу.
    """
    return Pagination(limit=limit, offset=offset)


PaginationDep = Annotated[Pagination, Depends(get_pagination)]
