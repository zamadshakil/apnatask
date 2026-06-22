import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis

from app.config import settings
from app.database import get_db

logger = logging.getLogger("apnatask")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Resource initialization on startup
    logger.info("Initializing application startup...")
    yield
    logger.info("Shutting down application...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Hyperlocal services marketplace backend",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/", tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint that verifies connectivity to PostgreSQL (with PostGIS),
    Redis, and RabbitMQ (Celery).
    """
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "rabbitmq": "unknown"
    }
    
    # 1. Test Database (and PostGIS extension presence)
    try:
        result = await db.execute(text("SELECT postgis_version();"))
        version = result.scalar()
        health_status["database"] = f"connected (PostGIS: {version})"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(e)}"
        
    # 2. Test Redis
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        await redis_client.ping()
        health_status["redis"] = "connected"
        await redis_client.close()
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["redis"] = f"error: {str(e)}"
        
    # 3. Test RabbitMQ (Celery Broker Connection)
    try:
        from app.celery_app import celery_app
        # Connect to RabbitMQ using Celery's connection pool
        with celery_app.connection_for_write() as conn:
            conn.connect()
            health_status["rabbitmq"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["rabbitmq"] = f"error: {str(e)}"
        
    response_code = status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=response_code, content=health_status)
