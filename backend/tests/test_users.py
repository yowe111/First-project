"""
Тесты списка пользователей и проверки прав (роли).

Связка с задачами 2 и 3:
- GET /users доступен только с токеном;
- PATCH /users/{id}/role доступен только админу.
"""

from tests.helpers import login_user, register_user


async def _token(client, username: str, email: str, password: str = "12345") -> str:
    await register_user(client, username=username, email=email, password=password)
    login = await login_user(client, username=username, password=password)
    return login.json()["access_token"]


async def test_users_me_requires_auth(client):
    """Без токена /users/me закрыт."""
    response = await client.get("/users/me")
    assert response.status_code == 401


async def test_users_me_returns_current_user(client):
    token = await _token(client, "alex", "alex@example.com")
    response = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "alex"


async def test_list_users_requires_auth(client):
    """Задача 2: список только для авторизованных."""
    response = await client.get("/users")
    assert response.status_code == 401


async def test_list_users_returns_all(client):
    admin_token = await _token(client, "alex", "alex@example.com")
    await register_user(client, username="bob", email="bob@example.com")

    response = await client.get(
        "/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    names = {item["username"] for item in body["items"]}
    assert names == {"alex", "bob"}
    assert body["total"] == 2
    assert body["limit"] == 20
    assert body["offset"] == 0


async def test_change_role_forbidden_for_regular_user(client):
    """Обычный пользователь не может менять роли — 403."""
    await _token(client, "alex", "alex@example.com")  # первый = админ
    bob_token = await _token(client, "bob", "bob@example.com")

    response = await client.patch(
        "/users/1/role",
        json={"role": "user"},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert response.status_code == 403


async def test_admin_can_change_role(client):
    admin_token = await _token(client, "alex", "alex@example.com")
    bob = await register_user(client, username="bob", email="bob@example.com")
    bob_id = bob.json()["id"]

    response = await client.patch(
        f"/users/{bob_id}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


async def test_admin_cannot_change_own_role(client):
    admin_token = await _token(client, "alex", "alex@example.com")
    me = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.patch(
        f"/users/{me.json()['id']}/role",
        json={"role": "user"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
