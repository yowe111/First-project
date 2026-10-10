"""
auth.py — РЕГИСТРАЦИЯ И ВХОД.

Сравните с прежней версией: обработчик больше не строит запросы, не
хеширует пароли и не решает, кто станет администратором. Он делает ровно
три вещи — принимает данные, зовёт сервис, возвращает ответ.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from src.api.deps import AuthServiceDep
from src.schemas.auth import Token
from src.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать аккаунт",
)
async def register(data: UserCreate, auth: AuthServiceDep):
    """Первый пользователь в пустой базе становится admin, остальные — user."""
    return await auth.register(data)


@router.post("/login", response_model=Token, summary="Войти и получить токен")
async def login(
    # OAuth2PasswordRequestForm — стандартная форма входа: логин и пароль
    # приходят не JSON-ом, а как form-data. Благодаря этому работает
    # кнопка Authorize в /docs.
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth: AuthServiceDep,
):
    """Неверная пара → 401. Верная, но аккаунт заблокирован → 403."""
    user = await auth.authenticate(form.username, form.password)
    return Token(access_token=auth.issue_access_token(user))
