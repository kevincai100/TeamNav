"""Add recoverable workspace revisions."""

import sqlalchemy as sa

from alembic import op

revision = "20260729_0005"
down_revision = "20260729_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "site_id",
            sa.String(36),
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_site_revisions_site_created",
        "site_revisions",
        ["site_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_site_revisions_site_created", table_name="site_revisions")
    op.drop_table("site_revisions")
