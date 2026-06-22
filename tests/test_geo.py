import pytest
from app.database import ProviderModel, SessionLocal

# Tier 1 Tests: Geospatial Ingestion & Matching

def test_f1_t1_location_update_success(client):
    """Ingest valid coordinates for a provider and verify 200 OK and 'success'."""
    response = client.post("/api/v1/provider/location", json={
        "provider_id": 1,
        "latitude": 33.6844,
        "longitude": 73.0479
    })
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_f1_t1_matching_empty(client):
    """Query matching engine with no active providers and verify empty list."""
    response = client.get("/api/v1/matching?latitude=33.6844&longitude=73.0479&radius_km=5.0&category=Plumbing")
    assert response.status_code == 200
    assert response.json() == []

def test_f1_t1_matching_results(client):
    """Ingest provider coordinates, query matching engine and verify match."""
    # 1. Seed provider in mock DB
    db = SessionLocal()
    provider = ProviderModel(name="Ali", kyc_verified=True, category="Plumbing", phone="+923001234567")
    db.add(provider)
    db.commit()
    provider_id = provider.id
    db.close()

    # 2. Update provider location
    loc_resp = client.post("/api/v1/provider/location", json={
        "provider_id": provider_id,
        "latitude": 33.6844,
        "longitude": 73.0479
    })
    assert loc_resp.status_code == 200

    # 3. Match
    match_resp = client.get(f"/api/v1/matching?latitude=33.6844&longitude=73.0479&radius_km=5.0&category=Plumbing")
    assert match_resp.status_code == 200
    results = match_resp.json()
    assert len(results) == 1
    assert results[0]["provider_id"] == provider_id
    assert results[0]["name"] == "Ali"
    assert results[0]["kyc_verified"] is True
    assert results[0]["category"] == "Plumbing"

def test_f1_t1_matching_distance_calculation(client):
    """Ingest provider at known distance and verify calculated distance."""
    # Seed provider
    db = SessionLocal()
    provider = ProviderModel(name="Basit", kyc_verified=True, category="Electrician", phone="+923001234568")
    db.add(provider)
    db.commit()
    provider_id = provider.id
    db.close()

    # Coordinates: Lahore Mall Road (~10km from Lahore Airport)
    # Airport: Lat 31.5204, Lon 74.4101
    # Mall Road: Lat 31.5556, Lon 74.3587
    client.post("/api/v1/provider/location", json={
        "provider_id": provider_id,
        "latitude": 31.5556,
        "longitude": 74.3587
    })

    # Query matching from Airport
    match_resp = client.get(f"/api/v1/matching?latitude=31.5204&longitude=74.4101&radius_km=15.0&category=Electrician")
    assert match_resp.status_code == 200
    results = match_resp.json()
    assert len(results) == 1
    # Calculated distance using Haversine should be around 6.2 - 6.6 km
    assert 6.0 <= results[0]["distance_km"] <= 7.0

def test_f1_t1_matching_category_filter(client):
    """Ingest providers with different categories and verify category filtering works."""
    db = SessionLocal()
    p1 = ProviderModel(name="Plumber 1", kyc_verified=True, category="Plumbing", phone="+923001234501")
    p2 = ProviderModel(name="Electrician 1", kyc_verified=True, category="Electrician", phone="+923001234502")
    db.add(p1)
    db.add(p2)
    db.commit()
    p1_id, p2_id = p1.id, p2.id
    db.close()

    # Update locations
    client.post("/api/v1/provider/location", json={"provider_id": p1_id, "latitude": 33.6844, "longitude": 73.0479})
    client.post("/api/v1/provider/location", json={"provider_id": p2_id, "latitude": 33.6844, "longitude": 73.0479})

    # Match Plumbing
    plumbing_resp = client.get("/api/v1/matching?latitude=33.6844&longitude=73.0479&radius_km=5.0&category=Plumbing")
    plumbing_results = plumbing_resp.json()
    assert len(plumbing_results) == 1
    assert plumbing_results[0]["provider_id"] == p1_id

    # Match Electrician
    elec_resp = client.get("/api/v1/matching?latitude=33.6844&longitude=73.0479&radius_km=5.0&category=Electrician")
    elec_results = elec_resp.json()
    assert len(elec_results) == 1
    assert elec_results[0]["provider_id"] == p2_id


# Tier 2 Tests: Boundary & Corner Cases

def test_f1_t2_lat_out_of_bounds_low(client):
    """Submit provider latitude -90.1 and check for 422 validation error."""
    response = client.post("/api/v1/provider/location", json={
        "provider_id": 1,
        "latitude": -90.1,
        "longitude": 73.0479
    })
    assert response.status_code == 422

def test_f1_t2_lat_out_of_bounds_high(client):
    """Submit provider latitude 90.1 and check for 422 validation error."""
    response = client.post("/api/v1/provider/location", json={
        "provider_id": 1,
        "latitude": 90.1,
        "longitude": 73.0479
    })
    assert response.status_code == 422

def test_f1_t2_lon_out_of_bounds_low(client):
    """Submit provider longitude -180.1 and check for 422 validation error."""
    response = client.post("/api/v1/provider/location", json={
        "provider_id": 1,
        "latitude": 33.6844,
        "longitude": -180.1
    })
    assert response.status_code == 422

def test_f1_t2_lon_out_of_bounds_high(client):
    """Submit provider longitude 180.1 and check for 422 validation error."""
    response = client.post("/api/v1/provider/location", json={
        "provider_id": 1,
        "latitude": 33.6844,
        "longitude": 180.1
    })
    assert response.status_code == 422

def test_f1_t2_invalid_radius(client):
    """Submit matching request with radius <= 0, check for validation error."""
    # Negative radius
    response1 = client.get("/api/v1/matching?latitude=33.6844&longitude=73.0479&radius_km=-1.0&category=Plumbing")
    assert response1.status_code == 422

    # Zero radius
    response2 = client.get("/api/v1/matching?latitude=33.6844&longitude=73.0479&radius_km=0&category=Plumbing")
    assert response2.status_code == 422
