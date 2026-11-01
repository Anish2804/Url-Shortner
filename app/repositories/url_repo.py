"""URL repository with collision-resistant lookups and atomic consumption."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple
from sqlalchemy import and_, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import Url
from app.repositories.base import BaseRepository


class UrlRepository(BaseRepository[Url]):
    """Repository handling shortened URL queries, pagination, and atomic updates."""

    def __init__(self, session: AsyncSession):
        super().__init__(Url, session)

    async def get_by_short_code(self, short_code: str) -> Optional[Url]:
        stmt = select(Url).where(Url.short_code == short_code, Url.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_alias(self, custom_alias: str) -> Optional[Url]:
        stmt = select(Url).where(Url.custom_alias == custom_alias, Url.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_code_or_alias(self, code_or_alias: str) -> Optional[Url]:
        """High-performance lookup for redirect path matching either code or alias."""
        stmt = select(Url).where(
            or_(Url.short_code == code_or_alias, Url.custom_alias == code_or_alias),
            Url.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_code_or_alias(self, code_or_alias: str) -> bool:
        stmt = (
            select(func.count())
            .select_from(Url)
            .where(
                or_(Url.short_code == code_or_alias, Url.custom_alias == code_or_alias),
                Url.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0

    async def list_user_urls(
        self,
        user_id: uuid.UUID,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_expired: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[Sequence[Url], int]:
        """Paginated, filtered search of a user's URLs."""
        filters = [Url.user_id == user_id, Url.is_deleted.is_(False)]

        if search:
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    Url.short_code.ilike(term),
                    Url.custom_alias.ilike(term),
                    Url.title.ilike(term),
                    Url.original_url.ilike(term),
                )
            )

        if is_active is not None:
            filters.append(Url.is_active == is_active)

        now = datetime.now(timezone.utc)
        if is_expired is True:
            filters.append(and_(Url.expires_at.is_not(None), Url.expires_at <= now))
        elif is_expired is False:
            filters.append(or_(Url.expires_at.is_(None), Url.expires_at > now))

        # Total count query
        count_stmt = select(func.count()).select_from(Url).where(*filters)
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar() or 0

        # Sort order
        sort_col = getattr(Url, sort_by, Url.created_at)
        order_clause = desc(sort_col) if sort_order.lower() == "desc" else sort_col

        stmt = select(Url).where(*filters).order_by(order_clause).offset(skip).limit(limit)
        items_res = await self.session.execute(stmt)
        items = items_res.scalars().all()

        return items, total

    async def bulk_create(self, urls: List[Url]) -> List[Url]:
        """Persist a batch of URLs in a single flush."""
        self.session.add_all(urls)
        await self.session.flush()
        return urls

    async def soft_delete(self, url: Url) -> None:
        """Mark URL as deleted and deactivated without losing click history."""
        url.is_deleted = True
        url.is_active = False
        url.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def atomic_consume_one_time_link(self, url_id: uuid.UUID) -> bool:
        """Atomically mark a one-time link as consumed to prevent race conditions.
        
        Returns True if this exact request consumed it, False if already consumed.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(Url)
            .where(
                Url.id == url_id,
                Url.is_one_time.is_(True),
                Url.is_consumed.is_(False),
                Url.is_active.is_(True),
                Url.is_deleted.is_(False),
            )
            .values(is_consumed=True, consumed_at=now, is_active=False)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def increment_click_count(self, url_id: uuid.UUID, increment: int = 1) -> None:
        """Increment cached rollup click count on URL."""
        stmt = (
            update(Url)
            .where(Url.id == url_id)
            .values(click_count=Url.click_count + increment)
        )
        await self.session.execute(stmt)
        await self.session.flush()
