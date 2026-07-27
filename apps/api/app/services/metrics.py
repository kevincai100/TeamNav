from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SiteMetricDaily


class MetricsRecorder:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def increment(self, site_id: str, field: str) -> None:
        if field not in {"page_views", "link_clicks"}:
            raise ValueError("INVALID_METRIC")
        today = datetime.now(UTC).date()
        metric = await self.session.scalar(
            select(SiteMetricDaily).where(
                SiteMetricDaily.site_id == site_id, SiteMetricDaily.date == today
            )
        )
        if metric is None:
            metric = SiteMetricDaily(site_id=site_id, date=today, page_views=0, link_clicks=0)
            self.session.add(metric)
        setattr(metric, field, getattr(metric, field) + 1)

    async def report(self, site_id: str, days: int = 30) -> dict:
        since = datetime.now(UTC).date() - timedelta(days=days - 1)
        metrics = list(
            (
                await self.session.scalars(
                    select(SiteMetricDaily)
                    .where(SiteMetricDaily.site_id == site_id, SiteMetricDaily.date >= since)
                    .order_by(SiteMetricDaily.date)
                )
            ).all()
        )
        daily = [
            {
                "date": item.date.isoformat(),
                "page_views": item.page_views,
                "link_clicks": item.link_clicks,
            }
            for item in metrics
        ]
        return {
            "totals": {
                "page_views": sum(item.page_views for item in metrics),
                "link_clicks": sum(item.link_clicks for item in metrics),
            },
            "daily": daily,
        }
