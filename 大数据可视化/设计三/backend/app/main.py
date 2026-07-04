from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.db.seed import seed_test_user

# Import models so they are registered on Base.metadata
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create all tables on startup
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_test_user(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)