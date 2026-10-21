"""Начальная схема БД «Дивидендного календаря» (MVP).

Соответствует design/backend/2026-10-19_database-schema_backend.md.

Revision ID: 001_initial
Revises:
Create Date: 2026-10-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tickers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("short_name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=512), nullable=True),
        sa.Column("isin", sa.String(length=12), nullable=True),
        sa.Column("board", sa.String(length=16), nullable=True),
        sa.Column("lot_size", sa.Integer(), nullable=True),
        sa.Column("logo_url", sa.String(length=512), nullable=True),
        sa.Column("last_price", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("price_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dsi", sa.SmallInteger(), nullable=True),
        sa.Column("dsi_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "dsi IS NULL OR (dsi >= 0 AND dsi <= 100)", name="ck_tickers_dsi_range"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", name="uq_tickers_ticker"),
    )

    op.create_table(
        "shareholder_meetings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("meeting_date", sa.Date(), nullable=False),
        sa.Column("meeting_type", sa.String(length=16), nullable=False),
        sa.Column(
            "dividend_question", sa.Boolean(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column("dividend_period", sa.String(length=16), nullable=True),
        sa.Column("dividend_per_share", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "dividend_per_share IS NULL OR dividend_per_share >= 0",
            name="ck_meetings_dividend_per_share_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["ticker_id"],
            ["tickers.id"],
            name="fk_meetings_ticker",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ticker_id", "meeting_date", "meeting_type", name="uq_meetings_business_key"
        ),
    )
    op.create_index("ix_meetings_date", "shareholder_meetings", ["meeting_date"])

    op.create_table(
        "record_dates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("meeting_id", sa.Integer(), nullable=True),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column(
            "kind",
            sa.String(length=32),
            server_default=sa.text("'dividend_payment'"),
            nullable=False,
        ),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ticker_id"],
            ["tickers.id"],
            name="fk_record_dates_ticker",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["meeting_id"],
            ["shareholder_meetings.id"],
            name="fk_record_dates_meeting",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ticker_id", "record_date", "kind", name="uq_record_dates_business_key"
        ),
    )
    op.create_index("ix_record_dates_date", "record_dates", ["record_date"])
    op.create_index("ix_record_dates_ticker_kind", "record_dates", ["ticker_id", "kind"])

    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("threshold_days", sa.Integer(), server_default=sa.text("7"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ticker_id"],
            ["tickers.id"],
            name="fk_watchlist_ticker",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker_id", name="uq_watchlist_ticker"),
    )


def downgrade() -> None:
    op.drop_table("watchlist_items")
    op.drop_index("ix_record_dates_ticker_kind", table_name="record_dates")
    op.drop_index("ix_record_dates_date", table_name="record_dates")
    op.drop_table("record_dates")
    op.drop_index("ix_meetings_date", table_name="shareholder_meetings")
    op.drop_table("shareholder_meetings")
    op.drop_table("tickers")
