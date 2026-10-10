"""
user.py — ПРОФИЛЬ, СПИСОК ЛЮДЕЙ, РОЛИ И БЛОКИРОВКИ.
"""

from src.core import security
from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.enums import UserRole
from src.models.user import User
from src.repositories.user import UserRepository
from src.schemas.user import PasswordChange, UserUpdate


class UserService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def get_or_fail(self, user_id: int) -> User:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Пользователь не найден")
        return user

    async def search(
        self,
        *,
        query: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[User], int]:
        return await self.users.search(query=query, limit=limit, offset=offset)

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        """Частичное обновление своего профиля.

        Пароль и роль через этот метод не меняются: для них есть отдельные
        операции со своими проверками.
        """
        if data.username is not None and data.username != user.username:
            if await self.users.username_taken(data.username, exclude_id=user.id):
                raise ConflictError("Пользователь с таким именем уже существует")
            user.username = data.username

        if data.email is not None and data.email != user.email:
            if await self.users.email_taken(data.email, exclude_id=user.id):
                raise ConflictError("Пользователь с такой почтой уже существует")
            user.email = data.email

        return await self.users.save(user)

    async def change_password(self, user: User, data: PasswordChange) -> None:
        """Сменить свой пароль.

        Неверный старый пароль — это 400, а не 401: человек уже вошёл,
        его личность подтверждена токеном, ошибка в содержании запроса.
        """
        if not security.verify_password(data.old_password, user.hashed_password):
            raise ValidationError("Неверный текущий пароль")

        user.hashed_password = security.hash_password(data.new_password)
        await self.users.commit()

    async def block(self, admin: User, user_id: int) -> User:
        """Заблокировать аккаунт.

        Запрет на блокировку самого себя — защита от ситуации, когда
        единственный администратор случайно лишает себя доступа и
        разблокировать его становится некому.
        """
        user = await self.get_or_fail(user_id)
        if user.id == admin.id:
            raise ValidationError("Нельзя заблокировать самого себя")

        user.is_active = False
        return await self.users.save(user)

    async def unblock(self, user_id: int) -> User:
        user = await self.get_or_fail(user_id)
        user.is_active = True
        return await self.users.save(user)

    async def change_role(self, admin: User, user_id: int, role: UserRole) -> User:
        """Сменить роль. Себе — нельзя, по той же причине, что и блокировка."""
        user = await self.get_or_fail(user_id)
        if user.id == admin.id:
            raise ValidationError("Нельзя изменить роль самому себе")

        user.role = role
        return await self.users.save(user)
