from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, text, create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator, Generator
from app.config import settings

# Modern Declarative Base for SQLAlchemy 2.0
class Base(DeclarativeBase):
    pass

class ProviderModel(Base):
    __tablename__ = "providers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    kyc_verified = Column(Boolean, default=False)
    category = Column(String, nullable=False)
    phone = Column(String, nullable=True)

class BookingModel(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=False)
    provider_id = Column(Integer, nullable=True)
    status = Column(String, default="pending")
    amount = Column(Float, default=0.0)
    transaction_id = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)

class WalletModel(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), unique=True, nullable=False)
    balance = Column(Float, default=0.0)

class BidModel(Base):
    __tablename__ = "bids"
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending")  # pending | accepted | rejected

class UserPushTokenModel(Base):
    __tablename__ = "user_push_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    role = Column(String, nullable=False) # "customer" | "provider"
    push_token = Column(String, nullable=False, unique=True)

# Synchronous engine and session maker
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Asynchronous engine and session maker
async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

def init_spatial_db() -> None:
    """
    Ensure the PostGIS extension is loaded in the PostgreSQL database.
    Should be called during application startup.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()
    except Exception as e:
        # Gracefully handle when running in environments without PostgreSQL/PostGIS (e.g. tests)
        pass

def get_db() -> Generator:
    """
    Dependency generator for synchronous database sessions.
    Useful for Celery tasks or standard sync endpoints.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency generator for asynchronous database sessions.
    Used in FastAPI endpoints.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

