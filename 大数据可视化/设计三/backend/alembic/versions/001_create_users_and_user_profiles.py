"""create users and user_profiles tables

Revision ID: 001
Revises:
Create Date: 2026-06-01
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("is_test_user", sa.Boolean, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("nickname", sa.String(64), nullable=False),
        sa.Column("gender", sa.String(16), nullable=False),
        sa.Column("age", sa.Integer, nullable=False),
        sa.Column("height_cm", sa.Float, nullable=False),
        sa.Column("weight_kg", sa.Float, nullable=False),
        sa.Column("body_fat_rate", sa.Float, nullable=True),
        sa.Column("activity_level", sa.String(32), nullable=False),
        sa.Column("health_goal", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_profiles")
    op.drop_table("users")
