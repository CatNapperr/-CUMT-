from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, DECIMAL, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class RoadSegment(Base):
    __tablename__ = "road_segment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(
        Enum("expressway", "arterial", "branch", name="road_type_enum"),
        nullable=False,
    )
    free_flow_speed: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    history: Mapped[list["TrafficHistory"]] = relationship(
        back_populates="road",
        cascade="all, delete-orphan",
    )


class TrafficHistory(Base):
    __tablename__ = "traffic_history"
    __table_args__ = (
        Index("idx_traffic_history_road_timestamp", "road_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    road_id: Mapped[int] = mapped_column(
        ForeignKey("road_segment.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
        index=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    speed: Mapped[float] = mapped_column(DECIMAL(5, 2), nullable=False)
    occupancy: Mapped[float] = mapped_column(DECIMAL(4, 2), nullable=False)

    road: Mapped[RoadSegment] = relationship(back_populates="history")
