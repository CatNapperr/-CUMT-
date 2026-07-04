"""create meals, meal_items, meal_item_alternatives tables

Revision ID: 002
Revises: 001
Create Date: 2026-06-01
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"


def upgrade() -> None:
    op.create_table(
        "meals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("meal_type", sa.String(32), nullable=False),
        sa.Column("meal_date", sa.Date(), nullable=False),
        sa.Column("time_string", sa.String(16), nullable=False),
        sa.Column("eaten_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calories", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("protein", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("carbs", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("fat", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("notes", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("image_id", sa.String(36), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("multiplier", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("is_collected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_liked", sa.Boolean(), nullable=True),
        sa.Column("health_score", sa.String(8), nullable=True),
        sa.Column("health_message", sa.Text(), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_meals_user_id_date", "meals", ["user_id", "meal_date"])
    op.create_index("ix_meals_meal_date", "meals", ["meal_date"])

    op.create_table(
        "meal_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("meal_id", sa.String(36), sa.ForeignKey("meals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("calories", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("protein", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("carbs", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("fat", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("weight_grams", sa.Integer(), nullable=True),
        sa.Column("weight_string", sa.String(128), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_meal_items_meal_id", "meal_items", ["meal_id"])

    op.create_table(
        "meal_item_alternatives",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("meal_item_id", sa.String(36), sa.ForeignKey("meal_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("calories", sa.Integer(), nullable=True),
        sa.Column("weight_string", sa.String(128), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_alt_meal_item_id", "meal_item_alternatives", ["meal_item_id"])


def downgrade() -> None:
    op.drop_table("meal_item_alternatives")
    op.drop_table("meal_items")
    op.drop_table("meals")
