"""Periodic aggregation job pre-computing daily and hourly analytics summaries."""

import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import desc, func, select

from app.core.logging import get_logger
from app.database.session import async_session_factory
from app.models.analytics import ClickEvent, DailyAggregate

logger = get_logger("aggregation_cron")


async def run_daily_rollup(target_date: Optional[date] = None) -> None:
    """Pre-compute daily rollups for all URLs with click activity."""
    if not target_date:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    logger.info("Starting daily analytics rollup for date: %s", target_date.isoformat())
    start_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(target_date, datetime.max.time(), tzinfo=timezone.utc)

    async with async_session_factory() as session:
        # Find all URLs with activity on this date
        urls_stmt = (
            select(ClickEvent.url_id)
            .where(ClickEvent.clicked_at >= start_dt, ClickEvent.clicked_at <= end_dt)
            .distinct()
        )
        url_ids = (await session.execute(urls_stmt)).scalars().all()

        for u_id in url_ids:
            # Query counts
            stats_stmt = (
                select(
                    func.count().label("total"),
                    func.count(func.distinct(ClickEvent.ip_hash)).label("unique"),
                    func.count().filter(ClickEvent.is_bot.is_(True)).label("bots"),
                )
                .where(ClickEvent.url_id == u_id, ClickEvent.clicked_at >= start_dt, ClickEvent.clicked_at <= end_dt)
            )
            stats = (await session.execute(stats_stmt)).fetchone()
            if not stats:
                continue

            async def get_breakdown_json(column):
                stmt = (
                    select(column, func.count().label("cnt"))
                    .where(ClickEvent.url_id == u_id, ClickEvent.clicked_at >= start_dt, ClickEvent.clicked_at <= end_dt)
                    .group_by(column)
                    .order_by(desc("cnt"))
                    .limit(10)
                )
                res = await session.execute(stmt)
                return json.dumps({str(r[0] or "Unknown"): r[1] for r in res.fetchall()})

            browsers_json = await get_breakdown_json(ClickEvent.browser)
            os_json = await get_breakdown_json(ClickEvent.os)
            devices_json = await get_breakdown_json(ClickEvent.device_type)
            countries_json = await get_breakdown_json(ClickEvent.country_code)
            referrers_json = await get_breakdown_json(ClickEvent.referrer_domain)

            # Check if record exists
            existing_stmt = select(DailyAggregate).where(DailyAggregate.url_id == u_id, DailyAggregate.date == target_date)
            existing = (await session.execute(existing_stmt)).scalar_one_or_none()

            if existing:
                existing.total_clicks = stats.total
                existing.unique_visitors = stats.unique
                existing.bot_clicks = stats.bots
                existing.browser_breakdown = browsers_json
                existing.os_breakdown = os_json
                existing.device_breakdown = devices_json
                existing.country_breakdown = countries_json
                existing.referrer_breakdown = referrers_json
            else:
                aggregate = DailyAggregate(
                    url_id=u_id,
                    date=target_date,
                    total_clicks=stats.total,
                    unique_visitors=stats.unique,
                    bot_clicks=stats.bots,
                    browser_breakdown=browsers_json,
                    os_breakdown=os_json,
                    device_breakdown=devices_json,
                    country_breakdown=countries_json,
                    referrer_breakdown=referrers_json,
                )
                session.add(aggregate)

        await session.commit()
    logger.info("Completed daily analytics rollup for %d URLs.", len(url_ids))


if __name__ == "__main__":
    asyncio.run(run_daily_rollup())
