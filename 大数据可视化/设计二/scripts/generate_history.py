from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import delete, insert

from backend.database import Base, SessionLocal, engine
from backend.models import RoadSegment, TrafficHistory
from backend.simulator.generator import calculate_current_traffic


def generate_history(hours: int = 72) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        roads = db.query(RoadSegment).order_by(RoadSegment.id.asc()).all()
        if not roads:
            raise RuntimeError("No road_segment records found. Run scripts/seed_roads.sql first.")

        end_time = datetime.now().replace(second=0, microsecond=0)
        start_time = end_time - timedelta(hours=hours)

        db.execute(
            delete(TrafficHistory).where(
                TrafficHistory.timestamp >= start_time,
                TrafficHistory.timestamp <= end_time,
            )
        )
        db.commit()

        batch = []
        current_time = start_time
        while current_time <= end_time:
            for road in roads:
                volume, speed, occupancy = calculate_current_traffic(road, current_time)
                batch.append(
                    {
                        "road_id": road.id,
                        "timestamp": current_time,
                        "volume": volume,
                        "speed": speed,
                        "occupancy": occupancy,
                    }
                )
            current_time += timedelta(minutes=5)

        if batch:
            db.execute(insert(TrafficHistory), batch)
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    generate_history()
