import pytest
from httpx import AsyncClient


async def managed_site(client: AsyncClient) -> tuple[str, str]:
    created = (
        await client.post(
            "/api/v1/sites",
            json={"name": "Import planning", "template_id": "blank", "theme": "light"},
        )
    ).json()
    slug = created["site"]["public_slug"]
    session = await client.post(
        f"/api/v1/manage/sites/{slug}/session",
        json={"edit_key": created["recovery_payload"]["edit_key"]},
    )
    return slug, session.json()["csrf_token"]


async def add_existing_link(client: AsyncClient, slug: str, csrf: str) -> None:
    category = await client.post(
        f"/api/v1/manage/sites/{slug}/categories",
        headers={"X-CSRF-Token": csrf},
        json={"name": "Engineering"},
    )
    await client.post(
        f"/api/v1/manage/sites/{slug}/links",
        headers={"X-CSRF-Token": csrf},
        json={
            "category_id": category.json()["id"],
            "name": "Existing",
            "url": "https://example.com/docs",
        },
    )


BOOKMARKS = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<DL><p>
  <DT><H3>Engineering</H3><DL><p>
    <DT><A HREF="https://example.com/docs#intro">Existing duplicate</A>
    <DT><A HREF="https://new.example.com/">New link</A>
  </DL><p>
  <DT><H3>Other</H3><DL><p>
    <DT><A HREF="https://new.example.com">Duplicate in file</A>
    <DT><A HREF="javascript:alert(1)">Unsupported</A>
  </DL><p>
</DL><p>"""


@pytest.mark.asyncio
async def test_bookmark_preview_explains_merge_and_duplicate_skips(
    client: AsyncClient,
) -> None:
    slug, csrf = await managed_site(client)
    await add_existing_link(client, slug, csrf)

    preview = await client.post(
        f"/api/v1/manage/sites/{slug}/bookmarks/preview",
        json={
            "mode": "merge",
            "duplicate_strategy": "skip",
            "html": BOOKMARKS,
        },
    )

    assert preview.status_code == 200
    assert preview.json() == {
        "mode": "merge",
        "duplicate_strategy": "skip",
        "source_categories": 2,
        "source_links": 4,
        "accepted_links": 3,
        "unsupported_links": 1,
        "duplicate_links": 2,
        "imported_links": 1,
        "created_categories": 0,
        "matched_categories": 1,
        "capacity": {
            "allowed": True,
            "categories": {
                "current": 1,
                "importing": 0,
                "after": 1,
                "limit": 200,
                "allowed": True,
            },
            "links": {
                "current": 1,
                "importing": 1,
                "after": 2,
                "limit": 2000,
                "allowed": True,
            },
        },
        "categories": [
            {
                "name": "Engineering",
                "source_links": 2,
                "imported_links": 1,
                "existing": True,
            }
        ],
    }

    imported = await client.post(
        f"/api/v1/manage/sites/{slug}/bookmarks/import",
        headers={"X-CSRF-Token": csrf},
        json={
            "mode": "merge",
            "duplicate_strategy": "skip",
            "html": BOOKMARKS,
        },
    )

    assert imported.status_code == 200
    assert imported.json()["imported_links"] == 1
    assert imported.json()["duplicate_links"] == 2
    managed = (await client.get(f"/api/v1/manage/sites/{slug}")).json()
    assert [category["name"] for category in managed["categories"]] == ["Engineering"]
    assert [link["name"] for link in managed["categories"][0]["links"]] == [
        "Existing",
        "New link",
    ]


@pytest.mark.asyncio
async def test_bookmark_import_can_keep_duplicates_and_create_new_categories(
    client: AsyncClient,
) -> None:
    slug, csrf = await managed_site(client)
    await add_existing_link(client, slug, csrf)

    imported = await client.post(
        f"/api/v1/manage/sites/{slug}/bookmarks/import",
        headers={"X-CSRF-Token": csrf},
        json={
            "mode": "merge",
            "duplicate_strategy": "keep",
            "html": BOOKMARKS,
        },
    )

    assert imported.status_code == 200
    assert imported.json()["imported_links"] == 3
    assert imported.json()["duplicate_links"] == 0
    assert imported.json()["created_categories"] == 1
    managed = (await client.get(f"/api/v1/manage/sites/{slug}")).json()
    assert [category["name"] for category in managed["categories"]] == [
        "Engineering",
        "Other",
    ]
    assert len(managed["categories"][0]["links"]) == 3
    assert len(managed["categories"][1]["links"]) == 1


@pytest.mark.asyncio
async def test_bookmark_replace_removes_existing_content_after_a_valid_plan(
    client: AsyncClient,
) -> None:
    slug, csrf = await managed_site(client)
    await add_existing_link(client, slug, csrf)

    imported = await client.post(
        f"/api/v1/manage/sites/{slug}/bookmarks/import",
        headers={"X-CSRF-Token": csrf},
        json={
            "mode": "replace",
            "duplicate_strategy": "skip",
            "html": BOOKMARKS,
        },
    )

    assert imported.status_code == 200
    assert imported.json()["imported_links"] == 2
    assert imported.json()["created_categories"] == 1
    managed = (await client.get(f"/api/v1/manage/sites/{slug}")).json()
    urls = {
        link["url"]
        for category in managed["categories"]
        for link in category["links"]
    }
    assert "https://example.com/docs" not in urls
    assert urls == {
        "https://example.com/docs#intro",
        "https://new.example.com/",
    }


@pytest.mark.asyncio
async def test_bookmark_preview_reports_capacity_before_writing(
    limited_client: AsyncClient,
) -> None:
    slug, csrf = await managed_site(limited_client)
    await add_existing_link(limited_client, slug, csrf)

    preview = await limited_client.post(
        f"/api/v1/manage/sites/{slug}/bookmarks/preview",
        json={
            "mode": "merge",
            "duplicate_strategy": "keep",
            "html": BOOKMARKS,
        },
    )

    assert preview.status_code == 200
    assert preview.json()["capacity"]["allowed"] is False
    assert preview.json()["capacity"]["links"] == {
        "current": 1,
        "importing": 3,
        "after": 4,
        "limit": 2,
        "allowed": False,
    }
    managed = (await limited_client.get(f"/api/v1/manage/sites/{slug}")).json()
    assert len(managed["categories"]) == 1
    assert len(managed["categories"][0]["links"]) == 1
