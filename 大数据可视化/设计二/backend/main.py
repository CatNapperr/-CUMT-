from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config import API_PREFIX
from backend.database import Base, engine, SessionLocal, get_db
from backend.routers.assistant import router as assistant_router
from backend.routers.insights import router as insights_router
from backend.routers.roads import router as roads_router
from backend.routers.traffic import router as traffic_router
from backend.schemas import HealthResponse
from backend.simulator.scheduler import create_scheduler

app = FastAPI(title="Traffic Monitoring API", version="1.0.0")
scheduler = create_scheduler(SessionLocal)
ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend"

app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="frontend-assets")
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="frontend-css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="frontend-js")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    if not scheduler.running:
        scheduler.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/index.html", include_in_schema=False)
def index_html() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/detail.html", include_in_schema=False)
def detail() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "detail.html")


@app.get(f"{API_PREFIX}/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        return {"status": "degraded", "database": "disconnected"}


app.include_router(roads_router, prefix=API_PREFIX)
app.include_router(insights_router, prefix=API_PREFIX)
app.include_router(traffic_router, prefix=API_PREFIX)
app.include_router(assistant_router, prefix=API_PREFIX)
