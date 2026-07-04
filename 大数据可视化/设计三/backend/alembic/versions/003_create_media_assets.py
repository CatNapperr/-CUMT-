"""create media_assets table

Revision ID: 003
Revises: 002
Create Date: 2026-06-01
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_media_assets_user_id_created_at", "media_assets", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_table("media_assets")
