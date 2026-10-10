"""
Тесты регистрации и входа — ровно то, что просили в задаче 5.

Каждый тест независим: фикстура client поднимает пустую базу заново.
"""

from tests.helpers import login_user, register_user


async def test_register_success(client):
    """Новый пользователь создаётся, пароль наружу не возвращается."""
    response = await register_user(client)

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alex"
    assert body["email"] == "alex@example.com"
    assert "password" not in body
    assert "hashed_password" not in body
    # Первый человек в пустой базе становится администратором.
    assert body["role"] == "admin"
    assert body["is_active"] is True


async def test_register_second_user_is_not_admin(client):
    """Второй зарегистрированный получает роль user, не admin."""
    await register_user(client, username="first", email="first@example.com")
    response = await register_user(
        client, username="second", email="second@example.com"
    )

    assert response.status_code == 201
    assert response.json()["role"] == "user"


async def test_register_duplicate_username(client):
    """Повторный логин — ошибка 400."""
    await register_user(client)
    response = await register_user(client, email="other@example.com")

    assert response.status_code == 400
    assert "именем" in response.json()["detail"]


async def test_register_duplicate_email(client):
    """Повторная почта — ошибка 400."""
    await register_user(client)
    response = await register_user(
        client, username="other", email="alex@example.com"
    )

    assert response.status_code == 400
    assert "почтой" in response.json()["detail"]


async def test_register_invalid_email(client):
    """Pydantic не пропускает строку, которая не похожа на почту (422)."""
    response = await client.post(
        "/auth/register",
        json={"username": "alex", "email": "not-an-email", "password": "12345"},
    )
    assert response.status_code == 422


async def test_login_success(client):
    """После регистрации вход выдаёт JWT-токен."""
    await register_user(client)
    response = await login_user(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert len(body["access_token"]) > 20


async def test_login_wrong_password(client):
    """Неверный пароль — 401, без подсказки «пароль неправильный» отдельно от логина."""
    await register_user(client)
    response = await login_user(client, password="wrong")

    assert response.status_code == 401


async def test_login_unknown_user(client):
    """Несуществующий логин — тоже 401, та же формулировка."""
    response = await login_user(client, username="ghost")

    assert response.status_code == 401
    assert "Неверное имя пользователя или пароль" in response.json()["detail"]
