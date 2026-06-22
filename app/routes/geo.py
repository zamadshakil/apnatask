from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import redis.asyncio as aioredis
from app.config import settings
from app.database import get_async_db, ProviderModel

router = APIRouter(prefix="/api/v1")

# Schema definitions
class LocationUpdate(BaseModel):
    provider_id: int
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

class ProviderMatchResponse(BaseModel):
    provider_id: int
    name: str
    latitude: float
    longitude: float
    distance_km: float
    kyc_verified: bool
    category: str

@router.post("/provider/location", status_code=status.HTTP_200_OK)
async def update_location(location: LocationUpdate):
    """
    Updates a service provider's current location in Redis spatial index (GEOADD).
    """
    redis_client = aioredis.from_url(settings.REDIS_URL)
    await redis_client.geoadd("providers_location", (location.longitude, location.latitude, location.provider_id))
    return {"status": "success"}

@router.get("/matching", response_model=list[ProviderMatchResponse])
async def match_providers(
    latitude: float,
    longitude: float,
    radius_km: float,
    category: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Fetches active, verified providers near a customer using GEO/PostGIS.
    """
    if radius_km <= 0:
        raise HTTPException(status_code=422, detail="Radius must be greater than zero")
    if not (-90.0 <= latitude <= 90.0):
        raise HTTPException(status_code=422, detail="Latitude must be between -90 and 90")
    if not (-180.0 <= longitude <= 180.0):
        raise HTTPException(status_code=422, detail="Longitude must be between -180 and 180")

    redis_client = aioredis.from_url(settings.REDIS_URL)
    
    try:
        results = await redis_client.georadius(
            "providers_location",
            longitude,
            latitude,
            radius_km,
            unit="km",
            withdist=True,
            withcoord=True
        )
    except Exception:
        return []

    if not results:
        return []

    provider_ids = [int(r[0]) for r in results]
    dist_map = {int(r[0]): float(r[1]) for r in results}
    coord_map = {int(r[0]): (float(r[2][0]), float(r[2][1])) for r in results}

    query = select(ProviderModel).where(
        ProviderModel.id.in_(provider_ids),
        ProviderModel.category == category,
        ProviderModel.kyc_verified == True
    )

    db_res = await db.execute(query)
    providers = db_res.scalars().all()

    response = []
    for p in providers:
        p_lon, p_lat = coord_map[p.id]
        response.append(ProviderMatchResponse(
            provider_id=p.id,
            name=p.name,
            latitude=p_lat,
            longitude=p_lon,
            distance_km=dist_map[p.id],
            kyc_verified=p.kyc_verified,
            category=p.category
        ))

    response.sort(key=lambda x: x.distance_km)
    return response

