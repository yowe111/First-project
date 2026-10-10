"""Задача 10: заметки и права на чужие записи."""

from tests.helpers import auth_header, token_for


async def _create_note(client, token: str, title: str = "Заголовок", body: str = "Текст"):
    return await client.post(
        "/notes",
        json={"title": title, "body": body},
        headers=auth_header(token),
    )


async def test_create_and_list_own_notes(client):
    token = await token_for(client, "alex", "alex@example.com")
    created = await _create_note(client, token)
    assert created.status_code == 201
    assert created.json()["title"] == "Заголовок"
    assert created.json()["owner_id"] == 1

    listing = await client.get("/notes", headers=auth_header(token))
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == created.json()["id"]


async def test_user_does_not_see_foreign_note(client):
    admin = await token_for(client, "alex", "alex@example.com")
    bob = await token_for(client, "bob", "bob@example.com")
    note = await _create_note(client, admin, title="Секрет")

    listing = await client.get("/notes", headers=auth_header(bob))
    assert listing.json()["total"] == 0

    foreign = await client.get(
        f"/notes/{note.json()['id']}",
        headers=auth_header(bob),
    )
    assert foreign.status_code == 404


async def test_user_cannot_list_all(client):
    await token_for(client, "alex", "alex@example.com")
    bob = await token_for(client, "bob", "bob@example.com")
    response = await client.get(
        "/notes",
        params={"all": True},
        headers=auth_header(bob),
    )
    assert response.status_code == 403


async def test_admin_lists_all_notes(client):
    admin = await token_for(client, "alex", "alex@example.com")
    bob = await token_for(client, "bob", "bob@example.com")
    await _create_note(client, admin, title="Админ")
    await _create_note(client, bob, title="Боб")

    response = await client.get(
        "/notes",
        params={"all": True},
        headers=auth_header(admin),
    )
    titles = {item["title"] for item in response.json()["items"]}
    assert titles == {"Админ", "Боб"}
    assert response.json()["total"] == 2


async def test_patch_only_own_note(client):
    admin = await token_for(client, "alex", "alex@example.com")
    bob = await token_for(client, "bob", "bob@example.com")
    note = await _create_note(client, admin)

    forbidden = await client.patch(
        f"/notes/{note.json()['id']}",
        json={"title": "Украл"},
        headers=auth_header(bob),
    )
    assert forbidden.status_code == 404

    ok = await client.patch(
        f"/notes/{note.json()['id']}",
        json={"title": "Обновил"},
        headers=auth_header(admin),
    )
    assert ok.status_code == 200
    assert ok.json()["title"] == "Обновил"


async def test_delete_own_note(client):
    token = await token_for(client, "alex", "alex@example.com")
    note = await _create_note(client, token)
    note_id = note.json()["id"]

    deleted = await client.delete(f"/notes/{note_id}", headers=auth_header(token))
    assert deleted.status_code == 204

    missing = await client.get(f"/notes/{note_id}", headers=auth_header(token))
    assert missing.status_code == 404


async def test_admin_can_delete_foreign_note(client):
    admin = await token_for(client, "alex", "alex@example.com")
    bob = await token_for(client, "bob", "bob@example.com")
    note = await _create_note(client, bob)
    note_id = note.json()["id"]

    deleted = await client.delete(f"/notes/{note_id}", headers=auth_header(admin))
    assert deleted.status_code == 204
