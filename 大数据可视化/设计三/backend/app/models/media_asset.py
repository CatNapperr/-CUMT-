import uuid
from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, Text, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class MediaAsset(Base):
    __tablename__ = "media_assets"

    __table_args__ = (
        Index("ix_media_assets_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128))
    storage_key: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
