# Milestone M1 Analysis and Design: Base App Setup & Dockerization

## 1. Architectural Summary & Container Services
ApnaTask Backend is structured as a containerised hyperlocal services marketplace API. The infrastructure coordinates 5 core services to handle REST/WebSockets, geospatial operations, pub/sub, and async background jobs.

| Service | Technology | Role in ApnaTask | Hostname | Port |
|---|---|---|---|---|
| **Database** | PostgreSQL + PostGIS (`postgis/postgis:16-3.4`) | Persistent relational database, with PostGIS spatial indexing for provider radius queries and verification checks. | `db` | `5432` |
| **In-Memory Store** | Redis (`redis:7.2-alpine`) | Serves a dual role: (1) Spatial Index (GEOADD/GEORADIUS) for high-frequency provider location tracking; (2) Pub/Sub message broker to cluster WebSocket instances. | `redis` | `6379` |
| **Task Broker** | RabbitMQ (`rabbitmq:3.12-management-alpine`) | Message queue broker for Celery asynchronous background tasks. Includes management UI for pipeline monitoring. | `rabbitmq` | `5672` (AMQP)<br>`15672` (HTTP Management) |
| **API Application** | FastAPI (`uvicorn` runner) | Serves REST endpoints (`/api/v1/provider/location`, `/api/v1/matching`) and WebSocket bidding interface (`/api/v1/ws/negotiation`). | `fastapi_app` | `8000` |
| **Background Worker** | Celery Worker | Asynchronously processes background tasks like booking timeouts (3-minute expiration) and mock push notification delivery. | `celery_worker` | N/A |

---

## 2. Directory Layout & Scaffolding Plan
Per `PROJECT.md`, the layout separates the source directory, configuration, tests, docker settings, and coordination metadata. 

```
/ (Project Root)
├── .agents/                    # Coordination metadata (e.g., explorer_m1_1)
├── app/                        # FastAPI application source code
│   ├── __init__.py
│   ├── main.py                 # App startup and route registrations
│   ├── config.py               # Pydantic BaseSettings class loading env variables
│   ├── database.py             # SQLAlchemy Async Engine and session builder
│   ├── celery_app.py           # Celery application declaration
│   └── tasks.py                # Celery async tasks (booking timeout, notification)
├── docker-compose.yml          # Local orchestration config for all services
├── Dockerfile                  # Multi-service python environment description
├── requirements.txt            # Package dependencies list
└── PROJECT.md                  # Project index
```

---

## 3. Dependency Specification (`requirements.txt`)
We have defined standard versions that allow full async support for FastAPI and SQLAlchemy 2.0:
- **`fastapi` & `uvicorn`**: Web server framework.
- **`sqlalchemy` & `asyncpg`**: Async DB operations.
- **`psycopg2-binary`**: Sync driver to support Alembic migrations.
- **`redis`**: Driver for spatial index reads/writes and Pub/Sub connections.
- **`celery`**: Asynchronous tasks processing framework.
- **`pydantic-settings`**: Pydantic V2 environment variable and settings loading.
- **`alembic`**: Database migration manager.
- **`httpx` & `pytest`**: Support for integration tests.

---

## 4. Multi-Service Container Orchestration Design
### 4.1. Dockerfile Layout
A unified Dockerfile is proposed to generate a single image used by both the `fastapi_app` and `celery_worker` services. This ensures version consistency across the worker and the app, reducing overhead.
- Base Image: `python:3.12-slim` (lightweight, minimal attack surface, has fast build times).
- System Dependencies: `curl` for container healthchecks and `postgresql-client` for inspecting DB states.
- Security: Runs under a non-root `appuser` (UID/GID 1000) to isolate container processes.

### 4.2. docker-compose.yml Setup
- Defines shared named volumes (`postgres_data`, `redis_data`, `rabbitmq_data`) for persistent state across restarts.
- Configures infrastructure health checks using native commands (`pg_isready` for Postgres, `redis-cli ping` for Redis, `rabbitmq-diagnostics ping` for RabbitMQ).
- Applies `depends_on` conditions (`service_healthy`) to ensure that the FastAPI app and Celery worker only start *after* the databases and brokers are fully active and accepting requests.

---

## 5. App Initialization & Active Health Checks (`GET /`)
A robust health check endpoint is implemented on `GET /` to verify the state of all downstream external services rather than returning a static `{"status": "ok"}` response.
1. **PostgreSQL**: Sends a query executing `SELECT postgis_version();` to the async database session. This verifies both read-write connectivity and that the `postgis` spatial extension is active in the database.
2. **Redis**: Pings the Redis database using `redis_client.ping()`.
3. **RabbitMQ**: Initiates a socket connection to RabbitMQ utilizing Celery's client connection pool (`celery_app.connection_for_write().connect()`).

If any checks fail, it logs the exception, returns `503 Service Unavailable`, and indicates which dependency failed, allowing orchestration engines (like Docker Compose or Kubernetes) to accurately assess backend readiness.
