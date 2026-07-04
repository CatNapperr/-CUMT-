import tempfile
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
from app.db.seed import seed_test_user

from app.models import User, UserProfile  # noqa: F401


@pytest.fixture(scope="function")
def db_session():
    # Use a temp file instead of :memory: so data persists across connections
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        seed_test_user(session)
        session.commit()
        yield session
    finally:
        session.close()
        engine.dispose()
        try:
            os.unlink(db_path)
        except PermissionError:
            pass  # Windows sometimes holds a lock; harmless


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(fastapi_app)
    yield test_client
    fastapi_app.dependency_overrides.clear()
