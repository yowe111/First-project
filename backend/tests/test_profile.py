"""Задачи 6–8: пагинация, свой профиль, смена пароля."""

from tests.helpers import auth_header, login_user, register_user, token_for


async def test_list_users_pagination(client):
    admin = await token_for(client, "alex", "alex@example.com")
    await register_user(client, username="bob", email="bob@example.com")
    await register_user(client, username="cara", email="cara@example.com")

    first = await client.get(
        "/users",
        params={"limit": 1, "offset": 0},
        headers=auth_header(admin),
    )
    assert first.status_code == 200
    assert first.json()["total"] == 3
    assert len(first.json()["items"]) == 1
    assert first.json()["items"][0]["username"] == "alex"

    second = await client.get(
        "/users",
        params={"limit": 1, "offset": 1},
        headers=auth_header(admin),
    )
    assert second.json()["items"][0]["username"] == "bob"


async def test_list_users_search(client):
    admin = await token_for(client, "alex", "alex@example.com")
    await register_user(client, username="bob", email="bob@example.com")

    response = await client.get(
        "/users",
        params={"q": "ALEX"},
        headers=auth_header(admin),
    )
    names = {item["username"] for item in response.json()["items"]}
    assert names == {"alex"}
    assert response.json()["total"] == 1


async def test_list_users_invalid_limit(client):
    admin = await token_for(client, "alex", "alex@example.com")
    too_small = await client.get(
        "/users", params={"limit": 0}, headers=auth_header(admin)
    )
    too_big = await client.get(
        "/users", params={"limit": 9999}, headers=auth_header(admin)
    )
    assert too_small.status_code == 422
    assert too_big.status_code == 422


async def test_update_me_username_keeps_token(client):
    """Токен хранит id, поэтому смена логина не разлогинивает."""
    token = await token_for(client, "alex", "alex@example.com")
    response = await client.patch(
        "/users/me",
        json={"username": "alexander"},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    me = await client.get("/users/me", headers=auth_header(token))
    assert me.status_code == 200
    assert me.json()["username"] == "alexander"


async def test_update_me_email(client):
    token = await token_for(client, "alex", "alex@example.com")
    response = await client.patch(
        "/users/me",
        json={"email": "new@example.com"},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    assert response.json()["email"] == "new@example.com"
    assert response.json()["username"] == "alex"

    me = await client.get("/users/me", headers=auth_header(token))
    assert me.json()["email"] == "new@example.com"


async def test_update_me_taken_email(client):
    token = await token_for(client, "alex", "alex@example.com")
    await register_user(client, username="bob", email="bob@example.com")

    response = await client.patch(
        "/users/me",
        json={"email": "bob@example.com"},
        headers=auth_header(token),
    )
    assert response.status_code == 400


async def test_update_me_invalid_email(client):
    token = await token_for(client, "alex", "alex@example.com")
    response = await client.patch(
        "/users/me",
        json={"email": "not-an-email"},
        headers=auth_header(token),
    )
    assert response.status_code == 422


async def test_change_password_success(client):
    token = await token_for(client, "alex", "alex@example.com")
    response = await client.post(
        "/users/me/password",
        json={"old_password": "12345", "new_password": "abcdef"},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    assert response.json()["detail"] == "Пароль обновлён"
    assert "password" not in response.json() or response.json().get("password") is None

    old = await login_user(client, password="12345")
    new = await login_user(client, password="abcdef")
    assert old.status_code == 401
    assert new.status_code == 200


async def test_change_password_wrong_old(client):
    token = await token_for(client, "alex", "alex@example.com")
    response = await client.post(
        "/users/me/password",
        json={"old_password": "nope", "new_password": "abcdef"},
        headers=auth_header(token),
    )
    assert response.status_code == 400


async def test_change_password_too_short(client):
    token = await token_for(client, "alex", "alex@example.com")
    response = await client.post(
        "/users/me/password",
        json={"old_password": "12345", "new_password": "ab"},
        headers=auth_header(token),
    )
    assert response.status_code == 422
