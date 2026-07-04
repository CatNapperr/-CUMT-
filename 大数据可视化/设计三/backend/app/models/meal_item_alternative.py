import uuid
from sqlalchemy import String, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class MealItemAlternative(Base):
    __tablename__ = "meal_item_alternatives"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meal_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meal_items.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128))
    calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_string: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


Index("ix_meal_item_alternatives_item_id", MealItemAlternative.meal_item_id)
