import sys
import os
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import kombu
mock_conn = MagicMock()
mock_pool = MagicMock()
mock_pool.limit = 10
mock_conn.Pool.return_value = mock_pool
kombu.Connection = MagicMock(return_value=mock_conn)

# Eager Celery config for testing
from app.celery_app import celery_app
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
)
from app.tasks import expire_booking
expire_booking.apply_async = MagicMock()

from app.database import Base, init_spatial_db
import redis
from app.config import settings
from sqlalchemy.pool import NullPool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import app.database

# Force NullPool for testing to prevent cross-test connection pollution & event loop mismatch errors
test_engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    echo=False
)
app.database.engine = test_engine
app.database.SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)
engine = test_engine

test_async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    poolclass=NullPool,
    echo=False
)
app.database.async_engine = test_async_engine
app.database.AsyncSessionLocal = async_sessionmaker(
    bind=test_async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

@pytest.fixture(scope="session", autouse=True)
def setup_database_and_services():
    # 1. Initialize PostGIS and database tables
    init_spatial_db()
    Base.metadata.create_all(bind=engine)
    yield

@pytest.fixture(autouse=True)
def clean_stores():
    """Clears DB and Redis state before each test."""
    from sqlalchemy import text
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f"TRUNCATE TABLE {table.name} RESTART IDENTITY CASCADE;"))
        conn.commit()

    r = redis.from_url(settings.REDIS_URL)
    r.flushdb()
    r.close()

@pytest.fixture
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c

@pytest.fixture
def jwt_helper():
    from jose import jwt
    def _create_token(user_id: int, role: str) -> str:
        payload = {"user_id": user_id, "role": role}
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return _create_token
