import pytest
from httpx import AsyncClient


async def managed_site(client: AsyncClient) -> tuple[str, str]:
    created = (
        await client.post(
            "/api/v1/sites",
            json={"name": "Recoverable workspace", "template_id": "blank", "theme": "light"},
        )
    ).json()
    slug = created["site"]["public_slug"]
    session = await client.post(
        f"/api/v1/manage/sites/{slug}/session",
        json={"edit_key": created["recovery_payload"]["edit_key"]},
    )
    return slug, session.json()["csrf_token"]


@pytest.mark.asyncio
async def test_deleted_content_can_be_restored_and_the_restore_can_be_undone(
    client: AsyncClient,
) -> None:
    slug, csrf = await managed_site(client)
    category = await client.post(
        f"/api/v1/manage/sites/{slug}/categories",
        headers={"X-CSRF-Token": csrf},
        json={"name": "Production", "icon": "P"},
    )
    assert category.status_code == 201
    deleted = await client.delete(
        f"/api/v1/manage/sites/{slug}/categories/{category.json()['id']}",
        headers={"X-CSRF-Token": csrf},
    )
    assert deleted.status_code == 204

    history = await client.get(f"/api/v1/manage/sites/{slug}/revisions")
    assert history.status_code == 200
    assert history.json()[0]["action"] == "category_deleted"
    assert history.json()[0]["category_count"] == 1
    assert history.json()[0]["link_count"] == 0

    restored = await client.post(
        f"/api/v1/manage/sites/{slug}/revisions/{history.json()[0]['id']}/restore",
        headers={"X-CSRF-Token": csrf},
    )
    assert restored.status_code == 200
    assert [item["name"] for item in restored.json()["categories"]] == ["Production"]

    after_restore = await client.get(f"/api/v1/manage/sites/{slug}/revisions")
    assert after_restore.json()[0]["action"] == "revision_restored"
    assert after_restore.json()[0]["category_count"] == 0

    undone = await client.post(
        f"/api/v1/manage/sites/{slug}/revisions/{after_restore.json()[0]['id']}/restore",
        headers={"X-CSRF-Token": csrf},
    )
    assert undone.status_code == 200
    assert undone.json()["categories"] == []
