"""Add daily site metrics."""

import sqlalchemy as sa

from alembic import op

revision = "20260727_0002"
down_revision = "20260727_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_metrics_daily",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "site_id",
            sa.String(36),
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("page_views", sa.Integer(), nullable=False),
        sa.Column("link_clicks", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_site_metrics_daily_site_id", "site_metrics_daily", ["site_id"])
    op.create_index(
        "ux_site_metrics_daily_site_date",
        "site_metrics_daily",
        ["site_id", "date"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("site_metrics_daily")
