import uuid
from datetime import date, datetime
from sqlalchemy import (
    String, Integer, Float, Text, Date, DateTime,
    Boolean, ForeignKey, func, Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Meal(Base):
    __tablename__ = "meals"

    __table_args__ = (
        Index("ix_meals_user_id_date", "user_id", "meal_date"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(128))
    meal_type: Mapped[str] = mapped_column(String(32))
    meal_date: Mapped[date] = mapped_column(Date)
    time_string: Mapped[str] = mapped_column(String(16))
    eaten_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    calories: Mapped[int] = mapped_column(Integer, default=0)
    protein: Mapped[int] = mapped_column(Integer, default=0)
    carbs: Mapped[int] = mapped_column(Integer, default=0)
    fat: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    image_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    is_collected: Mapped[bool] = mapped_column(Boolean, default=False)
    is_liked: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    health_score: Mapped[str | None] = mapped_column(String(8), nullable=True)
    health_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
