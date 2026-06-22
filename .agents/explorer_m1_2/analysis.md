# Milestone M1 Analysis & Architectural Design - Base App Setup & Dockerization

## 1. Overview & Objective
The goal of Milestone M1 is to scaffold the base structure of the ApnaTask backend service, plan and configure a multi-container Docker environment, set up the base FastAPI application with a comprehensive health check, and prepare the core application configuration and database session managers.

ApnaTask is designed as a high-concurrency, hyperlocal services marketplace backend. It requires:
1. **FastAPI Application**: Serving APIs and WebSockets.
2. **PostgreSQL + PostGIS**: Storing relational data and supporting spatial queries.
3. **Redis**: Ingesting high-frequency location updates (via `GEOADD`/`GEORADIUS` commands) and serving as a WebSocket pub/sub clustering backplane.
4. **Celery + RabbitMQ**: Processing asynchronous background tasks (such as booking request expiration timeouts and push notification queuing).

---

## 2. Directory Layout & Scaffolding Plan
To adhere strictly to the project layout specified in `PROJECT.md`, the repository must be scaffolded as follows:

```
/ (Project Root)
├── .agents/                    # Coordination metadata (no source code here)
│   ├── orchestrator/
│   ├── sub_orch_impl/
│   ├── explorer_m1_2/          # This agent's directory
│   └── explorer_m1_3/
├── app/                        # FastAPI application source
│   ├── __init__.py             # Package init
│   ├── main.py                 # FastAPI application initialization & Health check
│   ├── config.py               # Settings and configuration loader (pydantic-settings)
│   ├── database.py             # SQLAlchemy engine & async session setup
│   ├── schemas.py              # Pydantic models (to be fully designed in M2/M3)
│   ├── routes/                 # API routers
│   │   ├── __init__.py
│   │   ├── geo.py              # Geospatial location and matching (placeholder for now)
│   │   └── ws.py               # WebSocket negotiation (placeholder for now)
│   ├── celery_app.py           # Celery application configuration
│   ├── tasks.py                # Celery background tasks
│   └── mock_integrations/      # Third-party mocks
│       ├── __init__.py
│       ├── payments.py         # Mock EasyPaisa/JazzCash escrow
│       └── sms.py              # Mock SendPK/Jazz Direct OTP
├── migrations/                 # Alembic or SQL migrations directory
├── tests/                      # Pytest suite
│   ├── conftest.py
│   ├── test_geo.py
│   ├── test_ws.py
│   ├── test_tasks.py
│   └── test_integrations.py
├── docker-compose.yml          # Container orchestration configuration
├── Dockerfile                  # Application service container configuration
├── requirements.txt            # Python dependencies list
└── PROJECT.md                  # Project index and status tracker
```

---

## 3. Core Infrastructure Design (`docker-compose.yml`)
The core environment will run inside Docker using `docker-compose.yml`. We have planned five services:
1. **db (PostgreSQL + PostGIS)**: Uses `postgis/postgis:15-3.3-alpine` to support spatial data types (`GEOMETRY`/`GEOGRAPHY`) and queries. Configured with a health check running `pg_isready`.
2. **redis**: Uses `redis:7-alpine`. It serves as the geospatial cache index and the pub/sub broker for WebSocket clustering. Evaluated via standard `redis-cli ping`.
3. **rabbitmq**: Uses `rabbitmq:3-management-alpine`. Serves as the high-throughput message broker for Celery. Equipped with a management interface on port `15672` for diagnostics.
4. **fastapi_app**: Builds from the local `Dockerfile`. Mounts local source in development (if needed, though standard is straight container run) and exposes port `8000`. Starts via `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.
5. **celery_worker**: Builds from the same `Dockerfile` but overrides the startup command to launch the celery daemon: `celery -A app.celery_app.celery worker --loglevel=info`.

To ensure container stability and avoid race conditions, both `fastapi_app` and `celery_worker` depend on `db`, `redis`, and `rabbitmq` being in `service_healthy` states before booting.

---

## 4. Dependencies (`requirements.txt`)
The Python dependency list has been selected to support all planned features through Milestones M1-M6:
* **FastAPI & Uvicorn**: High-performance async web framework and ASGI server.
* **Pydantic & Pydantic-Settings**: For validation, serialization, and clean settings configuration from environment files.
* **SQLAlchemy (v2.0+)**: Relational Database ORM.
* **GeoAlchemy2**: Integrates SQLAlchemy with PostGIS spatial query extensions.
* **asyncpg**: Async PostgreSQL driver to make the FastAPI application non-blocking.
* **psycopg2-binary**: Synchronous PostgreSQL driver required by Alembic for running database migrations.
* **alembic**: Database migration manager.
* **redis**: Async-capable python client for Redis connectivity.
* **celery**: Asynchronous task queue engine.
* **python-jose[cryptography]**: For JWT encryption, decryption, and verification, needed to authorize WebSocket bidding clients.
* **websockets**: For low-level WebSocket support.
* **pytest & httpx**: Testing tools to write unit and integration test suites.

---

## 5. Base App Setup & Health Check Route (`app/main.py`)
A clean, functional health check route `GET /` is implemented. It verifies the health of all dependent services:
1. **PostgreSQL Database Connectivity**: Runs a lightweight query `SELECT 1` using the async session.
2. **PostGIS Spatial Extension Availability**: Runs `SELECT PostGIS_Version()`. This confirms the PostGIS extension is loaded, which is a key requirement for the spatial tracking matching engine in M2.
3. **Redis Connectivity**: Pings the Redis instance.
4. **Error Handling**: Catch-all clauses catch any exceptions, log them using the standard logger, and report the detailed service failure.
5. **Response Code Management**: If any service is unhealthy, the endpoint returns an HTTP `503 Service Unavailable` status code to signal the container orchestration system. If all systems are operational, it returns `200 OK`.

---

## 6. Celery Worker Bootstrap Safeguard
If a Celery worker is run in the background (as in our docker-compose layout) and the target source code is empty or missing the Celery instantiation module, the worker container will crash immediately with `ModuleNotFoundError` or `AttributeError`. 
To safeguard against this in Milestone M1, we design:
* A minimal `app/celery_app.py` setting up the `celery` app instance, configuring RabbitMQ broker and Redis result backend.
* A minimal `app/tasks.py` defining placeholder tasks `expire_booking` and `send_push_notification` which will be fully implemented in M4.

This ensures that `docker-compose up` launches all services cleanly, passing all container health checks from day one.
