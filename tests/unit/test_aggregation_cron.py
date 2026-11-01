"""Unit and integration tests for analytics daily and hourly rollup jobs."""

import uuid
from datetime import date, datetime, timedelta, timezone
import pytest
from sqlalchemy import select

from app.database.session import async_session_factory
from app.models.analytics import ClickEvent, DailyAggregate
from app.models.url import Url
from app.models.user import User
from app.workers.aggregation_cron import run_daily_rollup


@pytest.mark.asyncio
async def test_run_daily_rollup():
    """Verify that run_daily_rollup correctly pre-computes visitor counts and categorical breakdowns."""
    target_date = date(2026, 10, 31)
    base_time = datetime(2026, 10, 31, 14, 30, 0, tzinfo=timezone.utc)

    uid = uuid.uuid4().hex[:6]
    async with async_session_factory() as session:
        # Create user & url
        user = User(
            email=f"cron_test_{uid}@example.com",
            username=f"cron_test_{uid}",
            hashed_password="hashed_dummy_password",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        test_url = Url(
            user_id=user.id,
            original_url="https://example.com/target-rollup",
            short_code=f"cron_{uid}",
            is_active=True,
        )
        session.add(test_url)
        await session.flush()

        # Insert 3 click events: 2 human, 1 bot; 2 unique IPs
        c1 = ClickEvent(
            url_id=test_url.id,
            short_code=test_url.short_code,
            clicked_at=base_time,
            ip_hash="ip_hash_1",
            device_type="desktop",
            browser="Chrome",
            os="Windows",
            country_code="US",
            referrer_domain="google.com",
            is_bot=False,
        )
        c2 = ClickEvent(
            url_id=test_url.id,
            short_code=test_url.short_code,
            clicked_at=base_time + timedelta(minutes=10),
            ip_hash="ip_hash_1",  # Same IP (repeat visitor)
            device_type="desktop",
            browser="Chrome",
            os="Windows",
            country_code="US",
            referrer_domain="google.com",
            is_bot=False,
        )
        c3 = ClickEvent(
            url_id=test_url.id,
            short_code=test_url.short_code,
            clicked_at=base_time + timedelta(minutes=20),
            ip_hash="ip_hash_2",  # Different IP
            device_type="mobile",
            browser="Safari",
            os="iOS",
            country_code="IN",
            referrer_domain="twitter.com",
            is_bot=True,
        )
        session.add_all([c1, c2, c3])
        await session.commit()

        url_id = test_url.id

    # Execute rollup
    await run_daily_rollup(target_date)

    # Verify DailyAggregate row
    async with async_session_factory() as session:
        stmt = select(DailyAggregate).where(DailyAggregate.url_id == url_id, DailyAggregate.date == target_date)
        agg = (await session.execute(stmt)).scalar_one_or_none()

        assert agg is not None
        assert agg.total_clicks == 3
        assert agg.unique_visitors == 2
        assert agg.bot_clicks == 1
        assert "Chrome" in agg.browser_breakdown
        assert "iOS" in agg.os_breakdown
        assert "desktop" in agg.device_breakdown
        assert "US" in agg.country_breakdown
        assert "google.com" in agg.referrer_breakdown

    # Re-running the rollup should update the existing record idempotently
    await run_daily_rollup(target_date)

    async with async_session_factory() as session:
        stmt = select(DailyAggregate).where(DailyAggregate.url_id == url_id, DailyAggregate.date == target_date)
        aggs = (await session.execute(stmt)).scalars().all()
        assert len(aggs) == 1
