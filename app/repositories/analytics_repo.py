"""Analytics repository handling event recording and aggregation queries."""

import csv
import io
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import ClickEvent
from app.models.url import Url
from app.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository[ClickEvent]):
    """Repository handling click events and analytical summaries."""

    def __init__(self, session: AsyncSession):
        super().__init__(ClickEvent, session)

    async def insert_click(self, event: ClickEvent) -> ClickEvent:
        self.session.add(event)
        await self.session.flush()
        return event

    async def batch_insert_clicks(self, events: List[ClickEvent]) -> None:
        self.session.add_all(events)
        await self.session.flush()

    async def get_url_summary(
        self,
        url_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Aggregate all metrics for a given URL across the date window."""
        filters = [ClickEvent.url_id == url_id]
        if start_date:
            filters.append(ClickEvent.clicked_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc))
        if end_date:
            filters.append(ClickEvent.clicked_at <= datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc))

        # Overall counts
        stats_stmt = (
            select(
                func.count().label("total_clicks"),
                func.count(func.distinct(ClickEvent.ip_hash)).label("unique_visitors"),
                func.count().filter(ClickEvent.is_bot.is_(True)).label("bot_clicks"),
            )
            .where(*filters)
        )
        stats_res = await self.session.execute(stats_stmt)
        stats_row = stats_res.fetchone()
        total_clicks = stats_row.total_clicks if stats_row else 0
        unique_visitors = stats_row.unique_visitors if stats_row else 0
        bot_clicks = stats_row.bot_clicks if stats_row else 0

        async def get_breakdown(column, limit: int = 10) -> List[Dict[str, Any]]:
            if total_clicks == 0:
                return []
            stmt = (
                select(column, func.count().label("count"))
                .where(*filters)
                .group_by(column)
                .order_by(desc("count"))
                .limit(limit)
            )
            res = await self.session.execute(stmt)
            items = []
            for row in res.fetchall():
                cat = str(row[0] or "Unknown")
                cnt = row[1]
                pct = round((cnt / total_clicks) * 100, 2)
                items.append({"category": cat, "count": cnt, "percentage": pct})
            return items

        devices = await get_breakdown(ClickEvent.device_type)
        browsers = await get_breakdown(ClickEvent.browser)
        os_list = await get_breakdown(ClickEvent.os)
        countries = await get_breakdown(ClickEvent.country_code)
        referrers = await get_breakdown(ClickEvent.referrer_domain)

        # Time series by day
        date_trunc = func.date(ClickEvent.clicked_at)
        ts_stmt = (
            select(
                date_trunc.label("day"),
                func.count().label("clicks"),
                func.count(func.distinct(ClickEvent.ip_hash)).label("unique_visitors"),
            )
            .where(*filters)
            .group_by(date_trunc)
            .order_by(date_trunc.asc())
        )
        ts_res = await self.session.execute(ts_stmt)
        time_series = [
            {
                "date_or_hour": str(row.day),
                "clicks": row.clicks,
                "unique_visitors": row.unique_visitors,
            }
            for row in ts_res.fetchall()
        ]

        return {
            "total_clicks": total_clicks,
            "unique_visitors": unique_visitors,
            "bot_clicks": bot_clicks,
            "time_series": time_series,
            "devices": devices,
            "browsers": browsers,
            "operating_systems": os_list,
            "countries": countries,
            "referrers": referrers,
        }

    async def get_user_overview(
        self,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Aggregate platform metrics for all links belonging to a user."""
        urls_stmt = select(Url).where(Url.user_id == user_id, Url.is_deleted.is_(False))
        urls_res = await self.session.execute(urls_stmt)
        urls = urls_res.scalars().all()
        url_ids = [u.id for u in urls]

        if not url_ids:
            return {
                "total_urls": 0,
                "total_clicks": 0,
                "total_unique_visitors": 0,
                "total_bot_clicks": 0,
                "top_urls": [],
                "daily_traffic": [],
            }

        filters = [ClickEvent.url_id.in_(url_ids)]
        if start_date:
            filters.append(ClickEvent.clicked_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc))
        if end_date:
            filters.append(ClickEvent.clicked_at <= datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc))

        stats_stmt = (
            select(
                func.count().label("total_clicks"),
                func.count(func.distinct(ClickEvent.ip_hash)).label("unique_visitors"),
                func.count().filter(ClickEvent.is_bot.is_(True)).label("bot_clicks"),
            )
            .where(*filters)
        )
        stats_res = await self.session.execute(stats_stmt)
        stats_row = stats_res.fetchone()

        top_urls_stmt = (
            select(Url)
            .where(Url.id.in_(url_ids))
            .order_by(desc(Url.click_count))
            .limit(10)
        )
        top_urls_res = await self.session.execute(top_urls_stmt)
        top_urls = [
            {
                "short_code": u.short_code,
                "title": u.title,
                "original_url": u.original_url,
                "total_clicks": u.click_count,
            }
            for u in top_urls_res.scalars().all()
        ]

        # Daily traffic trend
        date_trunc = func.date(ClickEvent.clicked_at)
        daily_stmt = (
            select(
                date_trunc.label("day"),
                func.count().label("clicks"),
                func.count(func.distinct(ClickEvent.ip_hash)).label("unique_visitors"),
            )
            .where(*filters)
            .group_by(date_trunc)
            .order_by(date_trunc.asc())
        )
        daily_res = await self.session.execute(daily_stmt)
        daily_traffic = [
            {"date_or_hour": str(row.day), "clicks": row.clicks, "unique_visitors": row.unique_visitors}
            for row in daily_res.fetchall()
        ]

        return {
            "total_urls": len(urls),
            "total_clicks": stats_row.total_clicks if stats_row else 0,
            "total_unique_visitors": stats_row.unique_visitors if stats_row else 0,
            "total_bot_clicks": stats_row.bot_clicks if stats_row else 0,
            "top_urls": top_urls,
            "daily_traffic": daily_traffic,
        }

    async def export_clicks_csv(
        self,
        url_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> str:
        """Generate CSV string of click events for download."""
        filters = [ClickEvent.url_id == url_id]
        if start_date:
            filters.append(ClickEvent.clicked_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc))
        if end_date:
            filters.append(ClickEvent.clicked_at <= datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc))

        stmt = select(ClickEvent).where(*filters).order_by(ClickEvent.clicked_at.desc()).limit(10000)
        res = await self.session.execute(stmt)
        events = res.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Event ID",
            "Short Code",
            "Timestamp UTC",
            "Country",
            "City",
            "Device",
            "Browser",
            "OS",
            "Referrer Domain",
            "Is Bot",
        ])

        for ev in events:
            writer.writerow([
                str(ev.id),
                ev.short_code,
                ev.clicked_at.isoformat(),
                ev.country_code or "Unknown",
                ev.city or "Unknown",
                ev.device_type,
                ev.browser,
                ev.os,
                ev.referrer_domain or "Direct",
                ev.is_bot,
            ])

        return output.getvalue()
