import pytest
from httpx import AsyncClient

from app.services.maintenance import LinkProbeResult, probe_url


async def managed_site(client: AsyncClient) -> tuple[str, str]:
    created = (
        await client.post(
            "/api/v1/sites",
            json={"name": "Maintained workspace", "template_id": "blank", "theme": "light"},
        )
    ).json()
    slug = created["site"]["public_slug"]
    session = await client.post(
        f"/api/v1/manage/sites/{slug}/session",
        json={"edit_key": created["recovery_payload"]["edit_key"]},
    )
    return slug, session.json()["csrf_token"]


async def add_link(
    client: AsyncClient,
    slug: str,
    csrf: str,
    category_id: str,
    name: str,
    url: str,
) -> dict:
    response = await client.post(
        f"/api/v1/manage/sites/{slug}/links",
        headers={"X-CSRF-Token": csrf},
        json={"category_id": category_id, "name": name, "url": url},
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_probe_blocks_private_network_targets_without_requesting_them() -> None:
    result = await probe_url(
        "http://127.0.0.1:8080/admin",
        timeout_seconds=1,
        allow_private_networks=False,
    )

    assert result == LinkProbeResult(status="blocked", error="private_network")


@pytest.mark.asyncio
async def test_owner_can_check_links_and_disable_confirmed_broken_links(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slug, csrf = await managed_site(client)
    category = (
        await client.post(
            f"/api/v1/manage/sites/{slug}/categories",
            headers={"X-CSRF-Token": csrf},
            json={"name": "Services"},
        )
    ).json()
    healthy = await add_link(
        client,
        slug,
        csrf,
        category["id"],
        "Healthy",
        "https://healthy.example.com",
    )
    broken = await add_link(
        client,
        slug,
        csrf,
        category["id"],
        "Gone",
        "https://gone.example.com",
    )

    async def fake_probe(
        url: str,
        *,
        timeout_seconds: float,
        allow_private_networks: bool,
    ) -> LinkProbeResult:
        del timeout_seconds, allow_private_networks
        if "healthy" in url:
            return LinkProbeResult(status="healthy", status_code=204)
        return LinkProbeResult(status="broken", status_code=404, error="http_404")

    monkeypatch.setattr("app.services.maintenance.probe_url", fake_probe)
    configured = await client.patch(
        f"/api/v1/manage/sites/{slug}",
        headers={"X-CSRF-Token": csrf},
        json={
            "maintenance_config": {
                "link_check_enabled": True,
                "check_interval_hours": 24,
            }
        },
    )
    assert configured.status_code == 200
    assert configured.json()["maintenance_config"]["link_check_enabled"] is True

    checked = await client.post(
        f"/api/v1/manage/sites/{slug}/maintenance/check",
        headers={"X-CSRF-Token": csrf},
        json={"limit": 50},
    )

    assert checked.status_code == 200
    assert checked.json()["checked"] == 2
    assert checked.json()["statuses"] == {"healthy": 1, "broken": 1}
    maintenance = await client.get(f"/api/v1/manage/sites/{slug}/maintenance")
    assert maintenance.status_code == 200
    assert maintenance.json()["summary"] == {
        "unchecked": 0,
        "healthy": 1,
        "warning": 0,
        "broken": 1,
        "blocked": 0,
    }
    by_id = {link["id"]: link for link in maintenance.json()["links"]}
    assert by_id[healthy["id"]]["health_status"] == "healthy"
    assert by_id[healthy["id"]]["health_status_code"] == 204
    assert by_id[broken["id"]]["health_status"] == "broken"
    assert by_id[broken["id"]]["health_error"] == "http_404"

    disabled = await client.post(
        f"/api/v1/manage/sites/{slug}/maintenance/bulk",
        headers={"X-CSRF-Token": csrf},
        json={"action": "disable_broken"},
    )
    assert disabled.status_code == 200
    assert disabled.json() == {"updated": 1}
    public = (await client.get(f"/api/v1/public/sites/{slug}")).json()
    assert [link["name"] for link in public["categories"][0]["links"]] == ["Healthy"]


@pytest.mark.asyncio
async def test_transient_failures_need_two_checks_and_never_auto_disable(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slug, csrf = await managed_site(client)
    category = (
        await client.post(
            f"/api/v1/manage/sites/{slug}/categories",
            headers={"X-CSRF-Token": csrf},
            json={"name": "Services"},
        )
    ).json()
    link = await add_link(
        client,
        slug,
        csrf,
        category["id"],
        "Sometimes slow",
        "https://slow.example.com",
    )

    async def timeout_probe(
        url: str,
        *,
        timeout_seconds: float,
        allow_private_networks: bool,
    ) -> LinkProbeResult:
        del url, timeout_seconds, allow_private_networks
        return LinkProbeResult(status="warning", error="timeout")

    monkeypatch.setattr("app.services.maintenance.probe_url", timeout_probe)
    first = await client.post(
        f"/api/v1/manage/sites/{slug}/maintenance/check",
        headers={"X-CSRF-Token": csrf},
        json={"limit": 50},
    )
    second = await client.post(
        f"/api/v1/manage/sites/{slug}/maintenance/check",
        headers={"X-CSRF-Token": csrf},
        json={"limit": 50},
    )

    assert first.json()["statuses"] == {"warning": 1}
    assert second.json()["statuses"] == {"broken": 1}
    report = (await client.get(f"/api/v1/manage/sites/{slug}/maintenance")).json()
    checked = next(item for item in report["links"] if item["id"] == link["id"])
    assert checked["health_consecutive_failures"] == 2
    assert checked["is_enabled"] is True
    public = (await client.get(f"/api/v1/public/sites/{slug}")).json()
    assert public["categories"][0]["links"][0]["id"] == link["id"]
