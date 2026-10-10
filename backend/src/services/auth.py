"""
auth.py — РЕГИСТРАЦИЯ, ВХОД И РАЗБОР ТОКЕНА.

Сервис — это слой бизнес-правил. Он отвечает на вопросы «можно ли так
делать» и «что произойдёт», но ничего не знает ни про HTTP, ни про SQL:

- данные берёт у репозитория;
- об ошибках сообщает исключениями из `src/core/exceptions.py`.

Благодаря этому тот же `AuthService` можно вызвать из консольной команды
(«создай администратора») или из теста, не поднимая веб-сервер.
"""

from src.core import security
from src.core.exceptions import (
    AuthenticationError,
    ConflictError,
    PermissionDeniedError,
)
from src.enums import UserRole
from src.models.user import User
from src.repositories.user import UserRepository
from src.schemas.user import UserCreate


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def register(self, data: UserCreate) -> User:
        """Создать аккаунт.

        Первый пользователь в пустой базе становится администратором —
        иначе некому было бы выдать первую админскую роль.
        """
        existing = await self.users.get_by_username_or_email(
            data.username,
            data.email,
        )
        if existing is not None:
            # Говорим, что именно занято: иначе человек не поймёт,
            # какое из двух полей менять.
            if existing.username == data.username:
                raise ConflictError("Пользователь с таким именем уже существует")
            raise ConflictError("Пользователь с такой почтой уже существует")

        is_first_user = await self.users.count() == 0

        user = self.users.create(
            username=data.username,
            email=data.email,
            hashed_password=security.hash_password(data.password),
            role=UserRole.ADMIN if is_first_user else UserRole.USER,
            is_active=True,
        )
        return await self.users.save(user)

    async def authenticate(self, username: str, password: str) -> User:
        """Проверить пару логин/пароль и состояние аккаунта."""
        user = await self.users.get_by_username(username)

        # Проверяем логин и пароль одним условием и с одинаковым текстом
        # ошибки. Если отвечать «такого логина нет» отдельно, по ответам
        # API можно будет перебором собрать список существующих аккаунтов.
        if user is None or not security.verify_password(
            password, user.hashed_password
        ):
            raise AuthenticationError("Неверное имя пользователя или пароль")

        # Блокировку проверяем только после успешной пары логин/пароль:
        # посторонний не должен узнать, что такой аккаунт вообще есть.
        if not user.is_active:
            raise PermissionDeniedError("Аккаунт заблокирован")

        return user

    def issue_access_token(self, user: User) -> str:
        """Выдать токен. В `sub` кладём id, а не логин — его можно сменить."""
        return security.create_access_token(subject=str(user.id))

    async def get_user_by_token(self, token: str) -> User:
        """Восстановить пользователя по токену.

        Отсюда растёт защита эндпоинтов: обработчик, зависящий от текущего
        пользователя, без валидного токена даже не начнёт выполняться.
        """
        subject = security.decode_access_token(token)
        if subject is None:
            raise AuthenticationError()

        try:
            user_id = int(subject)
        except ValueError:
            # Токен подписан нами, но внутри не число — значит, он выдан
            # старой версией приложения, где в `sub` лежал логин.
            raise AuthenticationError() from None

        user = await self.users.get_by_id(user_id)
        if user is None:
            # Аккаунт удалили, а токен ещё жив.
            raise AuthenticationError("Пользователь не найден")

        # Даже с живым токеном заблокированный дальше не проходит.
        if not user.is_active:
            raise PermissionDeniedError("Аккаунт заблокирован")

        return user
