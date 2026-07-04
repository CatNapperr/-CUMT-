import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), primary_key=True
    )
    nickname: Mapped[str] = mapped_column(String(64))
    gender: Mapped[str] = mapped_column(String(16))
    age: Mapped[int] = mapped_column(Integer)
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    body_fat_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    activity_level: Mapped[str] = mapped_column(String(32))
    health_goal: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
