import pytest
from httpx import AsyncClient


async def create_site(client: AsyncClient, name: str = "Team Workspace") -> dict:
    response = await client.post(
        "/api/v1/sites",
        json={"name": name, "template_id": "blank", "theme": "light"},
    )
    assert response.status_code == 201
    return response.json()


async def manage(client: AsyncClient, created: dict) -> tuple[str, str]:
    slug = created["site"]["public_slug"]
    response = await client.post(
        f"/api/v1/manage/sites/{slug}/session",
        json={"edit_key": created["recovery_payload"]["edit_key"]},
    )
    assert response.status_code == 200
    return slug, response.json()["csrf_token"]


async def admin_login(client: AsyncClient) -> str:
    response = await client.post(
        "/api/v1/admin/session",
        json={"token": "test-admin-token-with-at-least-32-characters"},
    )
    assert response.status_code == 200
    return response.json()["csrf_token"]


@pytest.mark.asyncio
async def test_captcha_challenge_is_required_and_verified(captcha_client: AsyncClient) -> None:
    missing = await captcha_client.post(
        "/api/v1/sites",
        json={"name": "Protected create", "template_id": "blank", "theme": "light"},
    )
    assert missing.status_code == 422
    assert missing.json()["detail"]["code"] == "CAPTCHA_REQUIRED"

    challenge = (await captcha_client.get("/api/v1/captcha/challenge")).json()
    wrong = await captcha_client.post(
        "/api/v1/sites",
        json={
            "name": "Protected create",
            "template_id": "blank",
            "theme": "light",
            "captcha_token": challenge["token"],
            "captcha_answer": "999",
        },
    )
    assert wrong.status_code == 422
    assert wrong.json()["detail"]["code"] == "CAPTCHA_INVALID"

    solved = await captcha_client.post(
        "/api/v1/sites",
        json={
            "name": "Protected create",
            "template_id": "blank",
            "theme": "light",
            "captcha_token": challenge["token"],
            "captcha_answer": str(challenge["test_answer"]),
        },
    )
    assert solved.status_code == 201


@pytest.mark.asyncio
async def test_admin_can_resolve_reports_and_disable_sites(client: AsyncClient) -> None:
    created = await create_site(client)
    slug = created["site"]["public_slug"]
    report = await client.post(
        f"/api/v1/public/sites/{slug}/reports",
        json={"reason": "phishing", "description": "Suspicious login page"},
    )
    csrf = await admin_login(client)

    dashboard = await client.get("/api/v1/admin/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["reports"][0]["id"] == report.json()["id"]

    resolved = await client.patch(
        f"/api/v1/admin/reports/{report.json()['id']}",
        headers={"X-CSRF-Token": csrf},
        json={"status": "resolved"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    disabled = await client.patch(
        f"/api/v1/admin/sites/{slug}",
        headers={"X-CSRF-Token": csrf},
        json={"is_disabled": True},
    )
    assert disabled.status_code == 200
    assert (await client.get(f"/api/v1/public/sites/{slug}")).status_code == 410


@pytest.mark.asyncio
async def test_bookmark_import_export_and_site_clone(client: AsyncClient) -> None:
    created = await create_site(client, "Source Workspace")
    slug, csrf = await manage(client, created)
    bookmarks = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<DL><p><DT><H3>Engineering</H3><DL><p>
<DT><A HREF="https://github.com" TAGS="code,git">GitHub</A>
<DT><A HREF="javascript:alert(1)">Unsafe</A>
</DL><p></DL><p>"""
    imported = await client.post(
        f"/api/v1/manage/sites/{slug}/bookmarks/import",
        headers={"X-CSRF-Token": csrf},
        json={"mode": "replace", "html": bookmarks},
    )
    assert imported.status_code == 200
    assert imported.json()["imported_categories"] == 1
    assert imported.json()["imported_links"] == 1

    exported = await client.get(f"/api/v1/manage/sites/{slug}/bookmarks/export")
    assert exported.status_code == 200
    assert "NETSCAPE-Bookmark-file-1" in exported.text
    assert "https://github.com" in exported.text

    cloned = await client.post(
        f"/api/v1/manage/sites/{slug}/clone",
        headers={"X-CSRF-Token": csrf},
        json={"name": "Cloned Workspace"},
    )
    assert cloned.status_code == 201
    assert cloned.json()["site"]["public_slug"] != slug
    clone_public = await client.get(f"/api/v1/public/sites/{cloned.json()['site']['public_slug']}")
    assert clone_public.json()["categories"][0]["links"][0]["name"] == "GitHub"


@pytest.mark.asyncio
async def test_daily_page_views_and_link_clicks_are_reported(client: AsyncClient) -> None:
    created = await create_site(client, "Measured Workspace")
    slug, csrf = await manage(client, created)
    category = await client.post(
        f"/api/v1/manage/sites/{slug}/categories",
        headers={"X-CSRF-Token": csrf},
        json={"name": "Tools"},
    )
    link = await client.post(
        f"/api/v1/manage/sites/{slug}/links",
        headers={"X-CSRF-Token": csrf},
        json={
            "category_id": category.json()["id"],
            "name": "Docs",
            "url": "https://example.com/docs",
        },
    )

    await client.get(f"/api/v1/public/sites/{slug}")
    clicked = await client.post(f"/api/v1/public/sites/{slug}/links/{link.json()['id']}/click")
    assert clicked.status_code == 204

    stats = await client.get(f"/api/v1/manage/sites/{slug}/stats")
    assert stats.status_code == 200
    assert stats.json()["totals"] == {"page_views": 1, "link_clicks": 1}
    assert stats.json()["daily"][0]["page_views"] == 1
    assert stats.json()["daily"][0]["link_clicks"] == 1


@pytest.mark.asyncio
async def test_account_collects_new_sites_and_can_claim_anonymous_sites(
    client: AsyncClient,
) -> None:
    registered = await client.post(
        "/api/v1/account/register",
        json={"email": "owner@example.com", "password": "correct-horse-battery"},
    )
    assert registered.status_code == 201
    assert registered.cookies.get("teamnav_account")
    account_csrf = registered.json()["csrf_token"]

    owned = await create_site(client, "Owned Workspace")
    owned_slug = owned["site"]["public_slug"]
    assert (await client.get(f"/api/v1/manage/sites/{owned_slug}")).status_code == 200
    account_updated = await client.patch(
        f"/api/v1/manage/sites/{owned_slug}",
        headers={"X-CSRF-Token": account_csrf},
        json={"description": "Managed through account session"},
    )
    assert account_updated.status_code == 200
    assert account_updated.json()["description"] == "Managed through account session"
    mine = await client.get("/api/v1/account/sites")
    assert [site["public_slug"] for site in mine.json()["sites"]] == [owned["site"]["public_slug"]]

    await client.post("/api/v1/account/logout")
    anonymous = await create_site(client, "Anonymous Workspace")
    slug, manage_csrf = await manage(client, anonymous)
    logged_in = await client.post(
        "/api/v1/account/login",
        json={"email": "OWNER@example.com", "password": "correct-horse-battery"},
    )
    assert logged_in.status_code == 200
    logged_in_csrf = logged_in.json()["csrf_token"]

    claimed = await client.post(
        f"/api/v1/manage/sites/{slug}/claim",
        headers={"X-CSRF-Token": manage_csrf},
    )
    assert claimed.status_code == 200
    account_edit_with_manage_cookie = await client.patch(
        f"/api/v1/manage/sites/{slug}",
        headers={"X-CSRF-Token": logged_in_csrf},
        json={"description": "Account credential wins when both cookies exist"},
    )
    assert account_edit_with_manage_cookie.status_code == 200
    mine = await client.get("/api/v1/account/sites")
    assert {site["name"] for site in mine.json()["sites"]} == {
        "Owned Workspace",
        "Anonymous Workspace",
    }

    public = await client.get(f"/api/v1/public/sites/{slug}")
    assert public.status_code == 200


@pytest.mark.asyncio
async def test_batch_links_accept_optional_tags(client: AsyncClient) -> None:
    created = await create_site(client)
    slug, csrf = await manage(client, created)
    category = await client.post(
        f"/api/v1/manage/sites/{slug}/categories",
        headers={"X-CSRF-Token": csrf},
        json={"name": "Resources"},
    )
    response = await client.post(
        f"/api/v1/manage/sites/{slug}/links/batch",
        headers={"X-CSRF-Token": csrf},
        json={
            "category_id": category.json()["id"],
            "lines": "Docs | https://example.com/docs | Handbook | docs,team\nStatus | https://status.example.com",
        },
    )
    assert response.status_code == 201
    assert response.json()[0]["tags"] == ["docs", "team"]
    assert response.json()[1]["tags"] == []
