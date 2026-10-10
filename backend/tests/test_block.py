"""Задача 9: блокировка аккаунта."""

from tests.helpers import auth_header, login_user, register_user, token_for


async def test_admin_blocks_user_login(client):
    admin = await token_for(client, "alex", "alex@example.com")
    bob = await register_user(client, username="bob", email="bob@example.com")
    bob_id = bob.json()["id"]

    blocked = await client.post(
        f"/users/{bob_id}/block",
        headers=auth_header(admin),
    )
    assert blocked.status_code == 200
    assert blocked.json()["is_active"] is False

    login = await login_user(client, username="bob")
    assert login.status_code == 403
    assert "заблокирован" in login.json()["detail"]


async def test_blocked_token_stops_working(client):
    admin = await token_for(client, "alex", "alex@example.com")
    bob_token = await token_for(client, "bob", "bob@example.com")
    me = await client.get("/users/me", headers=auth_header(bob_token))
    bob_id = me.json()["id"]

    await client.post(f"/users/{bob_id}/block", headers=auth_header(admin))

    after = await client.get("/users/me", headers=auth_header(bob_token))
    assert after.status_code == 403


async def test_unblock_restores_login(client):
    admin = await token_for(client, "alex", "alex@example.com")
    bob = await register_user(client, username="bob", email="bob@example.com")
    bob_id = bob.json()["id"]

    await client.post(f"/users/{bob_id}/block", headers=auth_header(admin))
    await client.post(f"/users/{bob_id}/unblock", headers=auth_header(admin))

    login = await login_user(client, username="bob")
    assert login.status_code == 200


async def test_user_cannot_block(client):
    await token_for(client, "alex", "alex@example.com")
    bob_token = await token_for(client, "bob", "bob@example.com")

    response = await client.post(
        "/users/1/block",
        headers=auth_header(bob_token),
    )
    assert response.status_code == 403


async def test_admin_cannot_block_self(client):
    admin = await token_for(client, "alex", "alex@example.com")
    me = await client.get("/users/me", headers=auth_header(admin))
    response = await client.post(
        f"/users/{me.json()['id']}/block",
        headers=auth_header(admin),
    )
    assert response.status_code == 400
