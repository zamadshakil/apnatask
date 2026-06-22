# Proposed Design - Milestone M1 Base App Setup & Dockerization

## 1. Project Scaffolding Layout
The proposed directory and file layout conforms strictly to the schema defined in `PROJECT.md`. The files are mapped as follows:

```text
/ (Project Root)
├── .agents/                    # Coordination metadata (no source code here)
├── app/                        # FastAPI application source
│   ├── __init__.py             # Empty init module
│   ├── main.py                 # FastAPI application initialization & Health check
│   ├── config.py               # Settings and configuration via Pydantic settings
│   ├── database.py             # SQLAlchemy configuration & PostGIS init hook
│   ├── schemas.py              # Pydantic schemas (placeholder for M2)
│   ├── routes/                 # Endpoint routers
│   │   ├── __init__.py         # Init module exposing sub-routers
│   │   ├── geo.py              # Location updates and provider matching endpoints
│   │   └── ws.py               # WebSocket bidding & negotiation endpoints
│   ├── celery_app.py           # Celery application initialization
│   ├── tasks.py                # Celery background tasks
│   └── mock_integrations/      # Third-party mock interfaces
│       ├── __init__.py         # Init module
│       ├── payments.py         # Mock EasyPaisa/JazzCash escrow logic
│       └── sms.py              # Mock SendPK/Jazz Direct OTP SMS logic
├── migrations/                 # Alembic or raw SQL database migration scripts
├── tests/                      # Testing directory
│   ├── conftest.py
│   ├── test_geo.py
│   ├── test_ws.py
│   ├── test_tasks.py
│   └── test_integrations.py
├── docker-compose.yml          # Local orchestration configurations
├── Dockerfile                  # Application service container configuration
└── requirements.txt            # Python dependencies lists
```

---

## 2. Core Service Configurations

### A. Requirements Setup (`requirements.txt`)
The application dependencies are pinned to standard production-ready library versions, utilizing `psycopg2-binary` for synchronous operations (like Alembic migrations) and `asyncpg` for high-frequency asynchronous FastAPI requests. `GeoAlchemy2` is included for PostGIS object-relational mapping.
- Exact content is located at: `.agents/explorer_m1_3/proposed_requirements.txt`

### B. Docker Configuration (`Dockerfile`)
A multi-purpose, slim python container is proposed. It installs necessary system packages (`curl`, `build-essential`, `libpq-dev`), builds dependencies, copies codebase, and runs under a non-root security context (`appuser` with UID `8888`). The same image is used to run both the FastAPI application and the Celery worker by overriding CMD options.
- Exact content is located at: `.agents/explorer_m1_3/proposed_Dockerfile`

### C. Docker Compose Orchestration (`docker-compose.yml`)
The orchestration design includes:
1. `db`: PostGIS-enabled PostgreSQL 15 (`postgis/postgis:15-3.3`), using healthcheck checks with `pg_isready`.
2. `redis`: Redis 7 alpine for fast geospatial and Pub/Sub actions, using `redis-cli ping` healthcheck.
3. `rabbitmq`: RabbitMQ management image for task execution brokerage, using `rabbitmq-diagnostics -q ping` healthcheck.
4. `fastapi_app`: Rebuilds from `Dockerfile`, mounts the source code for local hot-reloads, and links dependencies only when they pass health checks.
5. `celery_worker`: Rebuilds from `Dockerfile`, runs the Celery worker command, and handles task processing.
- Exact content is located at: `.agents/explorer_m1_3/proposed_docker-compose.yml`

---

## 3. Database & Lifespan Setup (`app/database.py` & `app/config.py`)
- Config settings load variables from environment or a `.env` file via `BaseSettings` (using Pydantic v2).
- PostGIS setup: Upon startup, we invoke `init_spatial_db()` which executes `CREATE EXTENSION IF NOT EXISTS postgis;` on the sync engine connection. This ensures PostGIS features are always ready.
- Exact contents are located at:
  - Configuration: `.agents/explorer_m1_3/proposed_config.py`
  - Database: `.agents/explorer_m1_3/proposed_database.py`

---

## 4. Health Check Design (`GET /`)
To ensure robust monitoring, a health check route on `GET /` is designed. It asynchronously tests:
1. **Database Connection**: Triggers `SELECT 1` to verify DB driver and network connectivity.
2. **Redis In-Memory Store**: Pings Redis to guarantee the key-value/spatial index is reachable.
3. **RabbitMQ Broker**: Establishes a temporary connection check on the Celery broker URL.

If all services respond, it returns `200 OK` with JSON statistics. If any check fails, it raises an HTTP `503 Service Unavailable` with details of the degraded components.
- Exact content is located at: `.agents/explorer_m1_3/proposed_main.py`

---

## 5. Other Scaffolding Files (Celery & Mocks)
For completeness, basic structures have been drafted:
- Celery configurations: `.agents/explorer_m1_3/proposed_celery_app.py`
- Background tasks: `.agents/explorer_m1_3/proposed_tasks.py`
- Router files:
  - Geo API: `.agents/explorer_m1_3/proposed_routes_geo.py`
  - WebSockets: `.agents/explorer_m1_3/proposed_routes_ws.py`
- Third-party mocks:
  - Payments: `.agents/explorer_m1_3/proposed_mock_payments.py`
  - SMS Gateway: `.agents/explorer_m1_3/proposed_mock_sms.py`
