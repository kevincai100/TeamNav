import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.core.config import Settings


async def create_managed_site(client: AsyncClient, name: str = "产品团队") -> tuple[str, str]:
    created = (
        await client.post(
            "/api/v1/sites",
            json={"name": name, "template_id": "blank", "theme": "light"},
        )
    ).json()
    slug = created["site"]["public_slug"]
    accepted = await client.post(
        f"/api/v1/manage/sites/{slug}/session",
        json={"edit_key": created["recovery_payload"]["edit_key"]},
    )
    return slug, accepted.json()["csrf_token"]


def test_settings_reject_invalid_session_and_admin_security_values() -> None:
    with pytest.raises(ValidationError):
        Settings(account_session_days=0)
    with pytest.raises(ValidationError):
        Settings(admin_token="too-short")
    with pytest.raises(ValidationError):
        Settings(secret_key="replace-with-at-least-32-random-characters")
    with pytest.raises(ValidationError):
        Settings(admin_token="replace-with-a-long-random-admin-token")


@pytest.mark.asyncio
async def test_user_can_create_anonymous_site(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/sites",
        json={
            "name": "研发团队工作台",
            "description": "项目、发布和监控入口",
            "icon": "🧭",
            "template_id": "developer",
            "theme": "light",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["site"]["name"] == "研发团队工作台"
    assert payload["public_url"].startswith("http://test-web/s/")
    assert "?key=" in payload["manage_url"]
    assert len(payload["recovery_payload"]["edit_key"]) >= 43
    assert payload["recovery_payload"]["edit_key"] in payload["manage_url"]

    public_response = await client.get(
        f"/api/v1/public/sites/{payload['site']['public_slug']}"
    )
    assert public_response.status_code == 200
    assert "edit_key" not in public_response.text
    assert public_response.json()["categories"][0]["links"][0]["name"] == "GitHub"


@pytest.mark.asyncio
async def test_edit_key_establishes_management_session(client: AsyncClient) -> None:
    created = (
        await client.post(
            "/api/v1/sites",
            json={"name": "产品团队", "template_id": "blank", "theme": "light"},
        )
    ).json()
    slug = created["site"]["public_slug"]

    rejected = await client.post(
        f"/api/v1/manage/sites/{slug}/session", json={"edit_key": "x" * 43}
    )
    assert rejected.status_code == 401

    accepted = await client.post(
        f"/api/v1/manage/sites/{slug}/session",
        json={"edit_key": created["recovery_payload"]["edit_key"]},
    )
    assert accepted.status_code == 200
    assert accepted.cookies.get("teamnav_manage")
    assert accepted.json()["csrf_token"]

    managed = await client.get(f"/api/v1/manage/sites/{slug}")
    assert managed.status_code == 200
    assert managed.json()["name"] == "产品团队"
    assert "edit_key" not in managed.text


@pytest.mark.asyncio
async def test_owner_can_manage_categories_and_links(client: AsyncClient) -> None:
    slug, csrf = await create_managed_site(client)

    no_csrf = await client.post(
        f"/api/v1/manage/sites/{slug}/categories", json={"name": "产品资料"}
    )
    assert no_csrf.status_code == 403

    category_response = await client.post(
        f"/api/v1/manage/sites/{slug}/categories",
        headers={"X-CSRF-Token": csrf},
        json={"name": "产品资料", "description": "团队统一资料入口", "icon": "文"},
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    unsafe = await client.post(
        f"/api/v1/manage/sites/{slug}/links",
        headers={"X-CSRF-Token": csrf},
        json={"category_id": category_id, "name": "危险链接", "url": "javascript:alert(1)"},
    )
    assert unsafe.status_code == 422

    link_response = await client.post(
        f"/api/v1/manage/sites/{slug}/links",
        headers={"X-CSRF-Token": csrf},
        json={
            "category_id": category_id,
            "name": "产品手册",
            "url": "https://example.com/handbook",
            "description": "版本与使用说明",
            "tags": ["常用", "产品"],
            "is_pinned": True,
        },
    )
    assert link_response.status_code == 201

    public = await client.get(f"/api/v1/public/sites/{slug}")
    assert public.json()["categories"][0]["links"][0]["name"] == "产品手册"


@pytest.mark.asyncio
async def test_password_protected_site_requires_unlock(client: AsyncClient) -> None:
    created = (
        await client.post(
            "/api/v1/sites",
            json={
                "name": "内部导航",
                "template_id": "developer",
                "theme": "dark",
                "access_password": "shared-secret",
            },
        )
    ).json()
    slug = created["site"]["public_slug"]

    locked = await client.get(f"/api/v1/public/sites/{slug}")
    assert locked.status_code == 401
    assert "GitHub" not in locked.text
    metadata = await client.get(f"/api/v1/public/sites/{slug}/metadata")
    assert metadata.json() == {"name": "TeamNav", "allow_indexing": False}

    wrong = await client.post(
        f"/api/v1/public/sites/{slug}/unlock", json={"password": "wrong"}
    )
    assert wrong.status_code == 401

    unlocked = await client.post(
        f"/api/v1/public/sites/{slug}/unlock", json={"password": "shared-secret"}
    )
    assert unlocked.status_code == 204
    assert unlocked.cookies.get("teamnav_access")

    public = await client.get(f"/api/v1/public/sites/{slug}")
    assert public.status_code == 200
    assert public.json()["categories"][0]["links"][0]["name"] == "GitHub"


@pytest.mark.asyncio
async def test_owner_can_update_site_and_rotate_edit_key(client: AsyncClient) -> None:
    created = (
        await client.post(
            "/api/v1/sites",
            json={"name": "旧名称", "template_id": "blank", "theme": "light"},
        )
    ).json()
    slug = created["site"]["public_slug"]
    old_key = created["recovery_payload"]["edit_key"]
    session_response = await client.post(
        f"/api/v1/manage/sites/{slug}/session", json={"edit_key": old_key}
    )
    csrf = session_response.json()["csrf_token"]

    updated = await client.patch(
        f"/api/v1/manage/sites/{slug}",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "设计团队",
            "theme": "dark",
            "show_visit_count": True,
            "allow_indexing": True,
            "layout_config": {
                "accent_color": "#2563EB",
                "canvas_style": "soft",
                "card_style": "outline",
                "content_width": "wide",
                "columns": 3,
                "density": "compact",
                "header_alignment": "center",
                "wallpaper_url": "https://cdn.example.com/team-wallpaper.jpg",
                "wallpaper_fit": "cover",
                "wallpaper_position": "top",
                "wallpaper_overlay": 45,
            },
            "show_descriptions": False,
            "show_tags": False,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "设计团队"
    assert updated.json()["theme"] == "dark"
    assert updated.json()["layout_config"] == {
        "accent_color": "#2563EB",
        "canvas_style": "soft",
        "card_style": "outline",
        "content_width": "wide",
        "columns": 3,
        "density": "compact",
        "header_alignment": "center",
        "wallpaper_url": "https://cdn.example.com/team-wallpaper.jpg",
        "wallpaper_fit": "cover",
        "wallpaper_position": "top",
        "wallpaper_overlay": 45,
    }
    assert updated.json()["display_config"]["show_descriptions"] is False
    assert updated.json()["display_config"]["show_tags"] is False
    public_site = await client.get(f"/api/v1/public/sites/{slug}")
    assert public_site.json()["layout_config"]["accent_color"] == "#2563EB"
    assert public_site.json()["layout_config"]["wallpaper_url"] == (
        "https://cdn.example.com/team-wallpaper.jpg"
    )

    rejected_wallpaper = await client.patch(
        f"/api/v1/manage/sites/{slug}",
        headers={"X-CSRF-Token": csrf},
        json={"layout_config": {"wallpaper_url": "javascript:alert(1)"}},
    )
    assert rejected_wallpaper.status_code == 422

    metadata = await client.get(f"/api/v1/public/sites/{slug}/metadata")
    assert metadata.json() == {"name": "设计团队", "allow_indexing": True}

    rotated = await client.post(
        f"/api/v1/manage/sites/{slug}/rotate-edit-key",
        headers={"X-CSRF-Token": csrf},
    )
    assert rotated.status_code == 200
    new_key = rotated.json()["recovery_payload"]["edit_key"]
    assert new_key != old_key

    old = await client.post(
        f"/api/v1/manage/sites/{slug}/session", json={"edit_key": old_key}
    )
    assert old.status_code == 401
    new = await client.post(
        f"/api/v1/manage/sites/{slug}/session", json={"edit_key": new_key}
    )
    assert new.status_code == 200


@pytest.mark.asyncio
async def test_export_import_report_and_confirmed_delete(client: AsyncClient) -> None:
    slug, csrf = await create_managed_site(client, "临时项目组")
    category = await client.post(
        f"/api/v1/manage/sites/{slug}/categories",
        headers={"X-CSRF-Token": csrf},
        json={"name": "项目资源", "icon": "项"},
    )
    await client.post(
        f"/api/v1/manage/sites/{slug}/links",
        headers={"X-CSRF-Token": csrf},
        json={
            "category_id": category.json()["id"],
            "name": "项目主页",
            "url": "https://example.com/project",
        },
    )

    exported = await client.get(f"/api/v1/manage/sites/{slug}/export")
    assert exported.status_code == 200
    assert exported.json()["categories"][0]["links"][0]["name"] == "项目主页"
    assert "hash" not in exported.text
    assert "edit_key" not in exported.text

    report = await client.post(
        f"/api/v1/public/sites/{slug}/reports",
        json={"reason": "spam", "description": "测试举报"},
    )
    assert report.status_code == 201

    wrong = await client.request(
        "DELETE",
        f"/api/v1/manage/sites/{slug}",
        headers={"X-CSRF-Token": csrf},
        json={"confirm_name": "其他站点"},
    )
    assert wrong.status_code == 409

    deleted = await client.request(
        "DELETE",
        f"/api/v1/manage/sites/{slug}",
        headers={"X-CSRF-Token": csrf},
        json={"confirm_name": "临时项目组"},
    )
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/public/sites/{slug}")).status_code == 404


@pytest.mark.asyncio
async def test_anonymous_site_creation_is_rate_limited(client: AsyncClient) -> None:
    for index in range(5):
        response = await client.post(
            "/api/v1/sites",
            json={"name": f"站点 {index}", "template_id": "blank", "theme": "light"},
        )
        assert response.status_code == 201

    limited = await client.post(
        "/api/v1/sites",
        json={"name": "超出限制", "template_id": "blank", "theme": "light"},
    )
    assert limited.status_code == 429
    assert limited.json()["detail"]["code"] == "CREATE_RATE_LIMITED"
