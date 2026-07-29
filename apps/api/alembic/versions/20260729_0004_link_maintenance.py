"""Add link health and workspace maintenance settings."""

import sqlalchemy as sa

from alembic import op

revision = "20260729_0004"
down_revision = "20260727_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sites") as batch:
        batch.add_column(sa.Column("maintenance_config", sa.JSON(), nullable=True))
    with op.batch_alter_table("links") as batch:
        batch.add_column(
            sa.Column(
                "health_status",
                sa.String(16),
                nullable=False,
                server_default="unchecked",
            )
        )
        batch.add_column(sa.Column("health_status_code", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("health_error", sa.String(100), nullable=True))
        batch.add_column(sa.Column("health_checked_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column(
                "health_consecutive_failures",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("links") as batch:
        batch.drop_column("health_consecutive_failures")
        batch.drop_column("health_checked_at")
        batch.drop_column("health_error")
        batch.drop_column("health_status_code")
        batch.drop_column("health_status")
    with op.batch_alter_table("sites") as batch:
        batch.drop_column("maintenance_config")
