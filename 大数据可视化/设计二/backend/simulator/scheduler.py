from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from backend.models import RoadSegment, TrafficHistory
from backend.simulator.generator import calculate_current_traffic


def sample_current_traffic(session_factory: Callable[[], Session]) -> None:
    db = session_factory()
    try:
        roads = db.query(RoadSegment).order_by(RoadSegment.id.asc()).all()
        current_time = datetime.now()
        records = []
        for road in roads:
            volume, speed, occupancy = calculate_current_traffic(road, current_time)
            records.append(
                TrafficHistory(
                    road_id=road.id,
                    timestamp=current_time,
                    volume=volume,
                    speed=speed,
                    occupancy=occupancy,
                )
            )
        if records:
            db.add_all(records)
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def cleanup_old_history(session_factory: Callable[[], Session]) -> None:
    db = session_factory()
    try:
        threshold = datetime.now() - timedelta(days=7)
        db.query(TrafficHistory).filter(TrafficHistory.timestamp < threshold).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_scheduler(session_factory: Callable[[], Session]) -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        sample_current_traffic,
        IntervalTrigger(minutes=5),
        id="traffic_sampling",
        replace_existing=True,
        kwargs={"session_factory": session_factory},
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        cleanup_old_history,
        CronTrigger(hour=2, minute=0),
        id="traffic_cleanup",
        replace_existing=True,
        kwargs={"session_factory": session_factory},
        max_instances=1,
        coalesce=True,
    )
    return scheduler
