"""Initial production schema migration.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-01 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. roles
    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_roles_name", "roles", ["name"])

    # 2. users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, default=False),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, default=0),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])

    # 3. user_roles
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    )

    # 4. refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hashed_token", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, default=False),
        sa.Column("replaced_by_hash", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_refresh_tokens_hashed_token", "refresh_tokens", ["hashed_token"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_active", "refresh_tokens", ["hashed_token", "revoked", "expires_at"])

    # 5. api_keys
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("hashed_key", sa.String(64), nullable=False, unique=True),
        sa.Column("scopes", sa.String(255), nullable=False, default="urls:read,urls:write,analytics:read"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_api_keys_prefix", "api_keys", ["prefix"])
    op.create_index("ix_api_keys_hashed_key", "api_keys", ["hashed_key"])
    op.create_index("ix_api_keys_lookup", "api_keys", ["hashed_key", "is_active"])

    # 6. urls
    op.create_table(
        "urls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("short_code", sa.String(32), nullable=False, unique=True),
        sa.Column("custom_alias", sa.String(64), nullable=True, unique=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("redirect_http_code", sa.SmallInteger(), nullable=False, default=302),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("is_one_time", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_consumed", sa.Boolean(), nullable=False, default=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("click_count", sa.BigInteger(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_urls_short_code", "urls", ["short_code"])
    op.create_index("ix_urls_custom_alias", "urls", ["custom_alias"])
    op.create_index("ix_urls_redirect_lookup", "urls", ["short_code", "is_active", "is_deleted"])
    op.create_index("ix_urls_user_active", "urls", ["user_id", "is_active", "is_deleted"])

    # 7. click_events
    op.create_table(
        "click_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("url_id", sa.String(36), sa.ForeignKey("urls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("short_code", sa.String(32), nullable=False),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=False),
        sa.Column("anonymized_ip", sa.String(45), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("device_type", sa.String(32), nullable=False, default="desktop"),
        sa.Column("browser", sa.String(64), nullable=False, default="other"),
        sa.Column("os", sa.String(64), nullable=False, default="other"),
        sa.Column("referrer", sa.String(512), nullable=True),
        sa.Column("referrer_domain", sa.String(255), nullable=True),
        sa.Column("is_bot", sa.Boolean(), nullable=False, default=False),
    )
    op.create_index("ix_click_events_url_id", "click_events", ["url_id"])
    op.create_index("ix_click_events_short_code", "click_events", ["short_code"])
    op.create_index("ix_click_events_clicked_at", "click_events", ["clicked_at"])
    op.create_index("ix_click_events_url_time", "click_events", ["url_id", "clicked_at"])

    # 8. daily_aggregates
    op.create_table(
        "daily_aggregates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("url_id", sa.String(36), sa.ForeignKey("urls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("total_clicks", sa.Integer(), nullable=False, default=0),
        sa.Column("unique_visitors", sa.Integer(), nullable=False, default=0),
        sa.Column("bot_clicks", sa.Integer(), nullable=False, default=0),
        sa.Column("browser_breakdown", sa.Text(), nullable=True),
        sa.Column("os_breakdown", sa.Text(), nullable=True),
        sa.Column("device_breakdown", sa.Text(), nullable=True),
        sa.Column("country_breakdown", sa.Text(), nullable=True),
        sa.Column("referrer_breakdown", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_daily_aggregates_url_date", "daily_aggregates", ["url_id", "date"], unique=True)

    # 9. hourly_aggregates
    op.create_table(
        "hourly_aggregates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("url_id", sa.String(36), sa.ForeignKey("urls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hour_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_clicks", sa.Integer(), nullable=False, default=0),
        sa.Column("unique_visitors", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_hourly_aggregates_url_hour", "hourly_aggregates", ["url_id", "hour_timestamp"], unique=True)

    # 10. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="SUCCESS"),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_action_time", "audit_logs", ["action", "created_at"])

    # 11. abuse_reports
    op.create_table(
        "abuse_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("short_code", sa.String(32), nullable=False),
        sa.Column("reporter_email", sa.String(255), nullable=True),
        sa.Column("reason", sa.String(100), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="PENDING"),
        sa.Column("reviewed_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_abuse_reports_short_code", "abuse_reports", ["short_code"])
    op.create_index("ix_abuse_reports_status", "abuse_reports", ["status"])

    # 12. blocked_domains
    op.create_table(
        "blocked_domains",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("domain", sa.String(255), nullable=False, unique=True),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_blocked_domains_domain", "blocked_domains", ["domain"])

    # 13. custom_domains
    op.create_table(
        "custom_domains",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False, unique=True),
        sa.Column("verification_token", sa.String(64), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_custom_domains_lookup", "custom_domains", ["domain", "is_verified", "is_active"])


def downgrade() -> None:
    op.drop_table("custom_domains")
    op.drop_table("blocked_domains")
    op.drop_table("abuse_reports")
    op.drop_table("audit_logs")
    op.drop_table("hourly_aggregates")
    op.drop_table("daily_aggregates")
    op.drop_table("click_events")
    op.drop_table("urls")
    op.drop_table("api_keys")
    op.drop_table("refresh_tokens")
    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("roles")
