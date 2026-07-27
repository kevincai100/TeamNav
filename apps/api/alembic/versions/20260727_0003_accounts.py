"""Add optional accounts and site ownership."""

import sqlalchemy as sa

from alembic import op

revision = "20260727_0003"
down_revision = "20260727_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
    with op.batch_alter_table("sites") as batch:
        batch.add_column(sa.Column("owner_id", sa.String(36), nullable=True))
        batch.create_foreign_key(
            "fk_sites_owner_id", "users", ["owner_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_index("ix_sites_owner_id", ["owner_id"])


def downgrade() -> None:
    with op.batch_alter_table("sites") as batch:
        batch.drop_index("ix_sites_owner_id")
        batch.drop_constraint("fk_sites_owner_id", type_="foreignkey")
        batch.drop_column("owner_id")
    op.drop_table("user_sessions")
    op.drop_table("users")
