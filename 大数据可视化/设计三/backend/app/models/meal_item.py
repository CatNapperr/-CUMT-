import uuid
from datetime import datetime
from sqlalchemy import (
    String, Integer, Float, Text, DateTime,
    ForeignKey, func, Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class MealItem(Base):
    __tablename__ = "meal_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meals.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128))
    calories: Mapped[int] = mapped_column(Integer, default=0)
    protein: Mapped[int] = mapped_column(Integer, default=0)
    carbs: Mapped[int] = mapped_column(Integer, default=0)
    fat: Mapped[int] = mapped_column(Integer, default=0)
    weight_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_string: Mapped[str] = mapped_column(String(128), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


Index("ix_meal_items_meal_id", MealItem.meal_id)
