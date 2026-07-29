import asyncio
import ipaddress
import logging
import socket
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urljoin, urlsplit

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db import Database
from app.models import Link, Site

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LinkProbeResult:
    status: str
    status_code: int | None = None
    error: str | None = None


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


async def _validate_target(url: str, allow_private_networks: bool) -> None:
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("unsupported_protocol")
    if allow_private_networks:
        return
    if parsed.hostname.lower() == "localhost":
        raise ValueError("private_network")
    try:
        addresses = [ipaddress.ip_address(parsed.hostname)]
    except ValueError:
        try:
            resolved = await asyncio.get_running_loop().getaddrinfo(
                parsed.hostname,
                parsed.port or (443 if parsed.scheme.lower() == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as error:
            raise ValueError("dns_error") from error
        addresses = [ipaddress.ip_address(item[4][0]) for item in resolved]
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("private_network")


def _status_result(status_code: int) -> LinkProbeResult:
    if 200 <= status_code < 400 or status_code in {401, 403, 405}:
        return LinkProbeResult(status="healthy", status_code=status_code)
    if status_code in {404, 410}:
        return LinkProbeResult(
            status="broken", status_code=status_code, error=f"http_{status_code}"
        )
    return LinkProbeResult(
        status="warning", status_code=status_code, error=f"http_{status_code}"
    )


async def probe_url(
    url: str,
    *,
    timeout_seconds: float,
    allow_private_networks: bool,
) -> LinkProbeResult:
    current_url = url
    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=timeout_seconds,
        trust_env=False,
        headers={"User-Agent": "TeamNav-LinkChecker/1.0"},
    ) as client:
        for _ in range(5):
            try:
                await _validate_target(current_url, allow_private_networks)
            except ValueError as error:
                code = str(error)
                return LinkProbeResult(
                    status=(
                        "blocked"
                        if code in {"private_network", "unsupported_protocol"}
                        else "warning"
                    ),
                    error=code,
                )
            try:
                response = await client.head(current_url)
            except httpx.TimeoutException:
                return LinkProbeResult(status="warning", error="timeout")
            except httpx.ConnectError:
                return LinkProbeResult(status="warning", error="connection_error")
            except httpx.HTTPError:
                return LinkProbeResult(status="warning", error="request_error")
            if response.is_redirect and response.headers.get("location"):
                current_url = urljoin(current_url, response.headers["location"])
                continue
            return _status_result(response.status_code)
    return LinkProbeResult(status="warning", error="too_many_redirects")


class LinkMaintenanceService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def check_site(
        self,
        site: Site,
        *,
        force: bool,
        limit: int,
    ) -> dict:
        config = site.maintenance_config or {}
        cutoff = datetime.now(UTC) - timedelta(
            hours=int(config.get("check_interval_hours", 24))
        )
        links = list(
            (
                await self.session.scalars(
                    select(Link)
                    .where(Link.site_id == site.id)
                    .order_by(Link.health_checked_at.asc(), Link.sort_order.asc())
                )
            ).all()
        )
        due = [
            link
            for link in links
            if force
            or link.health_checked_at is None
            or _utc(link.health_checked_at) <= cutoff
        ]
        selected = due[: min(limit, self.settings.link_check_batch_size)]
        results = await asyncio.gather(
            *(
                probe_url(
                    link.url,
                    timeout_seconds=self.settings.link_check_timeout_seconds,
                    allow_private_networks=self.settings.link_check_allow_private_networks,
                )
                for link in selected
            )
        )
        checked_at = datetime.now(UTC)
        statuses: Counter[str] = Counter()
        for link, result in zip(selected, results, strict=True):
            status = result.status
            if status == "healthy":
                link.health_consecutive_failures = 0
            elif status in {"warning", "broken"}:
                link.health_consecutive_failures += 1
                if status == "warning" and link.health_consecutive_failures >= 2:
                    status = "broken"
            link.health_status = status
            link.health_status_code = result.status_code
            link.health_error = result.error
            link.health_checked_at = checked_at
            statuses[status] += 1
        await self.session.commit()
        return {
            "checked": len(selected),
            "remaining": max(len(due) - len(selected), 0),
            "statuses": dict(statuses),
        }

    async def report(self, site_id: str) -> dict:
        links = list(
            (
                await self.session.scalars(
                    select(Link)
                    .where(Link.site_id == site_id)
                    .order_by(Link.health_status, Link.name)
                )
            ).all()
        )
        statuses = ["unchecked", "healthy", "warning", "broken", "blocked"]
        summary = {status: 0 for status in statuses}
        for link in links:
            summary[link.health_status] = summary.get(link.health_status, 0) + 1
        return {
            "summary": summary,
            "links": [
                {
                    "id": link.id,
                    "name": link.name,
                    "url": link.url,
                    "is_enabled": link.is_enabled,
                    "health_status": link.health_status,
                    "health_status_code": link.health_status_code,
                    "health_error": link.health_error,
                    "health_checked_at": (
                        link.health_checked_at.isoformat() if link.health_checked_at else None
                    ),
                    "health_consecutive_failures": link.health_consecutive_failures,
                }
                for link in links
            ],
        }

    async def bulk(self, site_id: str, action: str) -> int:
        if action == "disable_broken":
            result = await self.session.execute(
                update(Link)
                .where(
                    Link.site_id == site_id,
                    Link.health_status == "broken",
                    Link.is_enabled.is_(True),
                )
                .values(is_enabled=False)
            )
        elif action == "reset_health":
            result = await self.session.execute(
                update(Link)
                .where(Link.site_id == site_id)
                .values(
                    health_status="unchecked",
                    health_status_code=None,
                    health_error=None,
                    health_checked_at=None,
                    health_consecutive_failures=0,
                )
            )
        else:
            raise ValueError("INVALID_MAINTENANCE_ACTION")
        await self.session.commit()
        return result.rowcount or 0


async def run_maintenance_cycle(database: Database, settings: Settings) -> None:
    async with database.sessions() as session:
        sites = list(
            (
                await session.scalars(
                    select(Site).where(Site.deleted_at.is_(None), Site.is_disabled.is_(False))
                )
            ).all()
        )
        for site in sites:
            if not (site.maintenance_config or {}).get("link_check_enabled", False):
                continue
            await LinkMaintenanceService(session, settings).check_site(
                site,
                force=False,
                limit=settings.link_check_batch_size,
            )


async def maintenance_loop(database: Database, settings: Settings) -> None:
    while True:
        try:
            await run_maintenance_cycle(database, settings)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Link maintenance cycle failed")
        await asyncio.sleep(settings.link_check_poll_seconds)
