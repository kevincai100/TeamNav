"""Initial TeamNav schema."""

import sqlalchemy as sa

from alembic import op

revision = "20260727_0001"
down_revision = None
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("public_slug", sa.String(24), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(32), nullable=False),
        sa.Column("theme", sa.String(16), nullable=False),
        sa.Column("layout_config", sa.JSON(), nullable=False),
        sa.Column("display_config", sa.JSON(), nullable=False),
        sa.Column("edit_key_hash", sa.String(64), nullable=False),
        sa.Column("access_password_hash", sa.String(128), nullable=True),
        sa.Column("password_version", sa.Integer(), nullable=False),
        sa.Column("allow_indexing", sa.Boolean(), nullable=False),
        sa.Column("is_disabled", sa.Boolean(), nullable=False),
        sa.Column("visit_count", sa.Integer(), nullable=False),
        *timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sites_public_slug", "sites", ["public_slug"], unique=True)
    op.create_table(
        "categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "site_id", sa.String(36), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(32), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_categories_site_sort", "categories", ["site_id", "sort_order"])
    op.create_table(
        "links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "site_id", sa.String(36), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "category_id",
            sa.String(36),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(32), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("open_mode", sa.String(16), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_links_category_sort", "links", ["category_id", "sort_order"])
    op.create_table(
        "manage_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "site_id", sa.String(36), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_manage_sessions_site_id", "manage_sessions", ["site_id"])
    op.create_index(
        "ix_manage_sessions_token_hash", "manage_sessions", ["token_hash"], unique=True
    )
    op.create_table(
        "access_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "site_id", sa.String(36), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("password_version", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_access_sessions_site_id", "access_sessions", ["site_id"])
    op.create_index(
        "ix_access_sessions_token_hash", "access_sessions", ["token_hash"], unique=True
    )
    op.create_table(
        "create_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ip_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_create_attempts_ip_hash", "create_attempts", ["ip_hash"])
    op.create_index("ix_create_attempts_created_at", "create_attempts", ["created_at"])
    op.create_table(
        "abuse_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "site_id", sa.String(36), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reporter_ip_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_abuse_reports_site_id", "abuse_reports", ["site_id"])


def downgrade() -> None:
    for table in [
        "abuse_reports",
        "create_attempts",
        "access_sessions",
        "manage_sessions",
        "links",
        "categories",
        "sites",
    ]:
        op.drop_table(table)
