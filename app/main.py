import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis
from kombu import Connection

from app.config import settings
from app.database import init_spatial_db, get_async_db
from app.celery_app import celery_app
from app.routes.geo import router as geo_router
from app.routes.ws import router as ws_router
from app.routes.bookings import router as bookings_router
from app.routes.wallet import router as wallet_router

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize PostGIS Extension
    logger.info("Initializing PostGIS extension if not exists...")
    try:
        init_spatial_db()
        logger.info("PostGIS database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize PostGIS database: {e}")
        # In production, we might want to fail startup, but let's log it clearly.
    
    yield
    
    # Shutdown logic (if any)
    logger.info("Shutting down application...")

app = FastAPI(
    title=settings.APP_NAME,
    description="Hyperlocal services marketplace backend with real-time tracking and bidding.",
    version="1.0.0",
    lifespan=lifespan
)

# Register routes
app.include_router(geo_router)
app.include_router(ws_router)
app.include_router(bookings_router)
app.include_router(wallet_router)

@app.get("/", tags=["Health"])
async def root_health_check(db: AsyncSession = Depends(get_async_db)):
    """
    Comprehensive health check route to verify status of:
    - FastAPI app initialization
    - PostgreSQL/PostGIS database connection
    - Redis connection
    - RabbitMQ (Celery Broker) connection
    """
    health_status = {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "services": {
            "database": "unknown",
            "redis": "unknown",
            "celery_broker": "unknown"
        }
    }
    
    is_healthy = True
    
    # 1. Check Database
    try:
        await db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "up"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["services"]["database"] = f"down: {str(e)}"
        is_healthy = False
        
    # 2. Check Redis
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        await redis_client.ping()
        health_status["services"]["redis"] = "up"
        await redis_client.aclose()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["services"]["redis"] = f"down: {str(e)}"
        is_healthy = False
        
    # 3. Check RabbitMQ / Celery Broker
    try:
        # Check if Celery broker can establish a connection
        broker_conn = Connection(settings.CELERY_BROKER_URL)
        broker_conn.connect()
        health_status["services"]["celery_broker"] = "up"
        broker_conn.release()
    except Exception as e:
        logger.error(f"Celery Broker health check failed: {e}")
        health_status["services"]["celery_broker"] = f"down: {str(e)}"
        is_healthy = False
        
    # Set overall status
    if not is_healthy:
        health_status["status"] = "degraded"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )
        
    return health_status
