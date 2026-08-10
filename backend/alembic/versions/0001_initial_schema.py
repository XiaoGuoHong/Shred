"""Create Shred's durable activity schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-10 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    ]


def upgrade() -> None:
    op.create_table(
        "source_messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("submission_uuid", sa.String(length=36), nullable=False, unique=True),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=128)),
        sa.Column("error_summary", sa.Text()),
        *_timestamps(),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.String(length=36), sa.ForeignKey("categories.id", ondelete="SET NULL")),
        sa.Column("origin", sa.String(length=32), nullable=False),
        sa.Column("origin_message_id", sa.String(length=36), sa.ForeignKey("source_messages.id", ondelete="SET NULL")),
        *_timestamps(),
        sa.UniqueConstraint("parent_id", "normalized_name"),
    )
    op.create_index(
        "uq_categories_root_normalized_name",
        "categories",
        ["normalized_name"],
        unique=True,
        sqlite_where=sa.text("parent_id IS NULL"),
    )
    op.create_table(
        "activity_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_message_id", sa.String(length=36), sa.ForeignKey("source_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("source_fragment", sa.Text()),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("occurrence_precision", sa.String(length=32)),
        sa.Column("part_of_day", sa.String(length=32)),
        sa.Column("category_id", sa.String(length=36), sa.ForeignKey("categories.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(length=32), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("source_message_id", "position"),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False, unique=True),
        *_timestamps()[:1],
    )
    op.create_table(
        "event_tags",
        sa.Column("event_id", sa.String(length=36), sa.ForeignKey("activity_events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.String(length=36), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "correction_memories",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_id", sa.String(length=36), sa.ForeignKey("activity_events.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("event_text", sa.Text(), nullable=False),
        sa.Column("original_category_id", sa.String(length=36), sa.ForeignKey("categories.id", ondelete="SET NULL")),
        sa.Column("final_category_id", sa.String(length=36), sa.ForeignKey("categories.id", ondelete="SET NULL")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
    )
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("api_base_url", sa.String(length=512), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("id = 1", name="ck_app_settings_singleton"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("correction_memories")
    op.drop_table("event_tags")
    op.drop_table("tags")
    op.drop_table("activity_events")
    op.drop_index("uq_categories_root_normalized_name", table_name="categories")
    op.drop_table("categories")
    op.drop_table("source_messages")
