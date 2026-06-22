import time
import logging
from fastapi import FastAPI, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis

from app.config import settings
from app.database import get_db

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    version="1.0.0"
)

@app.get("/", status_code=status.HTTP_200_OK)
async def health_check(response: Response, db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint that verifies the connectivity of external dependencies:
    - PostgreSQL Database (executes SELECT 1)
    - PostGIS Extension availability (executes SELECT PostGIS_Version())
    - Redis Cache & Spatial Index (sends ping)
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "database": "unknown",
            "postgis": "unknown",
            "redis": "unknown"
        }
    }
    
    # 1. Check PostgreSQL Database connection
    try:
        await db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["status"] = "unhealthy"
        health_status["services"]["database"] = f"unhealthy: {str(e)}"

    # 2. Check PostGIS Extension
    if health_status["services"]["database"] == "healthy":
        try:
            # Check if PostGIS extension is installed and functioning
            result = await db.execute(text("SELECT PostGIS_Version()"))
            postgis_version = result.scalar()
            health_status["services"]["postgis"] = f"healthy (version: {postgis_version})"
        except Exception as e:
            logger.error(f"PostGIS extension check failed: {e}")
            health_status["status"] = "unhealthy"
            health_status["services"]["postgis"] = f"unhealthy: {str(e)}"
    else:
        health_status["services"]["postgis"] = "unhealthy: database connection failed"

    # 3. Check Redis Connection
    try:
        # Create a connection pool and ping
        redis_client = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        pong = await redis_client.ping()
        if pong:
            health_status["services"]["redis"] = "healthy"
        else:
            health_status["status"] = "unhealthy"
            health_status["services"]["redis"] = "unhealthy: ping returned False"
        await redis_client.close()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["status"] = "unhealthy"
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"

    # Set response code to 503 if any service is unhealthy
    if health_status["status"] != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return health_status
