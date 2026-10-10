"""Общие хелперы запросов. Вынесены из conftest, чтобы тесты могли их импортировать."""

from httpx import AsyncClient, Response


async def register_user(
    client: AsyncClient,
    username: str = "alex",
    email: str = "alex@example.com",
    password: str = "12345",
) -> Response:
    return await client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    )


async def login_user(
    client: AsyncClient,
    username: str = "alex",
    password: str = "12345",
) -> Response:
    return await client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def token_for(
    client: AsyncClient,
    username: str,
    email: str,
    password: str = "12345",
) -> str:
    await register_user(client, username=username, email=email, password=password)
    login = await login_user(client, username=username, password=password)
    return login.json()["access_token"]
