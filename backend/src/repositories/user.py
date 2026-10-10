"""
user.py — ЗАПРОСЫ К ТАБЛИЦЕ `users`.

Здесь только то, что специфично для пользователей. Всё общее — `get_by_id`,
`count`, `paginate` — уже унаследовано от `BaseRepository`.
"""

from sqlalchemy import or_

from src.models.user import User
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User
    default_order_by = (User.id,)

    async def get_by_username(self, username: str) -> User | None:
        return await self.find_one(User.username == username)

    async def get_by_email(self, email: str) -> User | None:
        return await self.find_one(User.email == email)

    async def get_by_username_or_email(
        self,
        username: str,
        email: str,
    ) -> User | None:
        """Один запрос вместо двух — нужен при регистрации.

        Сервис потом сам разберётся, что именно занято: логин или почта.
        """
        return await self.find_one(
            or_(User.username == username, User.email == email)
        )

    async def username_taken(self, username: str, *, exclude_id: int | None = None) -> bool:
        """Занят ли логин кем-то ещё.

        `exclude_id` нужен при редактировании профиля: человек может
        «занять» своё же текущее имя, и это не должно считаться конфликтом.
        """
        conditions = [User.username == username]
        if exclude_id is not None:
            conditions.append(User.id != exclude_id)
        return await self.exists(*conditions)

    async def email_taken(self, email: str, *, exclude_id: int | None = None) -> bool:
        conditions = [User.email == email]
        if exclude_id is not None:
            conditions.append(User.id != exclude_id)
        return await self.exists(*conditions)

    async def search(
        self,
        *,
        query: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[User], int]:
        """Страница пользователей с поиском по логину и почте.

        `ilike` — сравнение без учёта регистра, `%` вокруг строки означает
        «где угодно внутри значения».
        """
        conditions = []
        if query:
            pattern = f"%{query}%"
            conditions.append(
                or_(User.username.ilike(pattern), User.email.ilike(pattern))
            )
        return await self.paginate(*conditions, limit=limit, offset=offset)
