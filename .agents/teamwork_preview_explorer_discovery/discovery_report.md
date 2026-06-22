# ApnaTask Backend Discovery Report

## 1. Executive Summary
This report summarizes the codebase discovery, architecture analysis, and infrastructure design for the ApnaTask backend service. Currently, the project is in the initial bootstrapping phase (**Milestone 1**). The project root directory contains only the `PROJECT.md` file and the `.agents` metadata folder. The implementation track (under `sub_orch_impl`) has proposed files for Milestone 1 drafted within `.agents/explorer_m1_3/` and `.agents/explorer_m1_1/`. No active implementation code or test files have been placed in the root directory yet. 

---

## 2. Infrastructure Setup & Docker Configuration
The infrastructure is orchestrated using Docker Compose, consisting of five core services:
1. **Database (`db`)**: Uses PostGIS-enabled PostgreSQL image (`postgis/postgis:15-3.3` or `postgis/postgis:16-3.4`). The `postgis` extension is initialized during app startup.
2. **Redis (`redis`)**: Serves as the high-speed in-memory store for geospatial coordinates (GEOADD/GEORADIUS) on DB 0 and the Celery result backend on DB 1.
3. **RabbitMQ (`rabbitmq`)**: RabbitMQ management image acts as the broker for Celery asynchronous tasks.
4. **FastAPI Application (`fastapi_app`)**: Rebuilt from a slim Python 3.11 Dockerfile, mounting the source code for hot-reloads and exposing port 8000.
5. **Celery Worker (`celery_worker`)**: Rebuilt from the same Dockerfile, running the Celery worker daemon (`celery -A app.celery_app.celery_app worker`).

---

## 3. Database Architecture & Config
- **ORM & Drivers**: Uses SQLAlchemy 2.0 with `DeclarativeBase`. Supports both synchronous operations (using `psycopg2-binary` for Alembic migrations and database setup) and asynchronous operations (using `asyncpg` for high-frequency FastAPI endpoints).
- **Lifespan Hook**: During FastAPI app startup, a lifespan context manager executes `init_spatial_db()` which runs `CREATE EXTENSION IF NOT EXISTS postgis;` using the synchronous database engine.
- **DB Sessions**:
  - `get_db()`: Synchronous dependency generator yielding a sync `SessionLocal`. Used by Celery tasks.
  - `get_async_db()`: Asynchronous dependency generator yielding an `AsyncSessionLocal`. Used by FastAPI routes.

---

## 4. FastAPI Routes & Schemas
### A. Routes
1. **Health Check (`GET /`)**:
   - Asynchronously verifies the connection to the PostgreSQL database (runs `SELECT 1` or `SELECT postgis_version()`), Redis (runs a `ping`), and RabbitMQ (checks if the Celery connection pool can connect).
   - Returns `200 OK` with service statuses if healthy, or `503 Service Unavailable` if any dependency is degraded.
2. **Provider Location Update (`POST /api/v1/provider/location`)**:
   - Endpoint to update a service provider's coordinates.
   - Body payload schema: `LocationUpdate` (`provider_id: int`, `latitude: float`, `longitude: float`).
   - Validates latitude in range `[-90, 90]` and longitude in range `[-180, 180]`.
   - Returns `{"status": "success"}` upon updating the Redis spatial index.
3. **Matching Engine (`GET /api/v1/matching`)**:
   - Query params: `latitude: float`, `longitude: float`, `radius_km: float`, `category: str`.
   - Fetches active providers within a geographical radius of the client's position.
   - Returns a list of `ProviderMatchResponse` objects.
4. **WebSocket Bidding (`WS /api/v1/ws/negotiation`)**:
   - Established using query parameter `token` (mock JWT containing `user_id` and `role`).
   - Connects clients (customers and providers) for real-time bid negotiations.

### B. Schemas
- **`LocationUpdate`**:
  - `provider_id`: `int`
  - `latitude`: `float` (with Pydantic validation `ge=-90.0, le=90.0`)
  - `longitude`: `float` (with Pydantic validation `ge=-180.0, le=180.0`)
- **`ProviderMatchResponse`**:
  - `provider_id`: `int`
  - `name`: `str`
  - `latitude`: `float`
  - `longitude`: `float`
  - `distance_km`: `float`
  - `kyc_verified`: `bool`
  - `category`: `str`

---

## 5. Redis Spatial Indexing
- **Ingestion**: Location updates via `POST /api/v1/provider/location` are written to Redis using `GEOADD`. The spatial index stores the longitude, latitude, and `provider_id` as the member name under a common key (e.g., `provider_locations`).
- **Querying**: The matching endpoint `GET /api/v1/matching` queries Redis using a radial spatial command (such as `GEORADIUS` or `GEOSEARCH`) to return list of `provider_id`s within the specified `radius_km`.
- **Filtering**: The retrieved list of `provider_id`s is cross-referenced in the PostgreSQL database to filter out inactive providers, filter by category (`category: str`), and verify KYC status (`kyc_verified: bool`).

---

## 6. Real-Time WebSocket Bidding Server
- **Authentication**: Establishes connection using standard FastAPI WebSocket endpoints. Requires a `token` query param which represents a mock JWT containing user identification and roles (`customer` or `provider`).
- **Pub/Sub Clustering**:
  - To support horizontal scaling across multiple FastAPI container instances, the WebSockets communicate using a Redis Pub/Sub channel backplane.
  - Each negotiation session maps to a Redis channel named `negotiation_{booking_id}`.
  - Upon connection, the socket handler spawns a listener task that subscribes to the channel. When the client sends a message, it is published to the channel and broadcast to all connected WebSocket clients on all application instances.
- **Message Exchange Format**:
  - Messages are sent and received in JSON:
    ```json
    {
      "type": "bid" | "chat" | "accept",
      "booking_id": int,
      "sender_id": int,
      "role": "customer" | "provider",
      "amount": float,
      "message": str
    }
    ```

---

## 7. Asynchronous Celery Tasks
- **Configuration**: Setup is located in `app/celery_app.py`. Integrates with RabbitMQ broker and Redis result backend. Time limits are configured (soft limit: 120s, hard limit: 180s) to keep hyperlocal tasks responsive.
- **Tasks**:
  1. `app.tasks.expire_booking(booking_id: int)`: 
     - Triggered automatically on booking request creation. Scheduled to execute with a `3-minute` delay.
     - When executed, queries the database to check if the booking state remains `"pending"`.
     - If pending, updates booking state to `"expired"` in the DB and triggers a push notification task.
  2. `app.tasks.send_push_notification(user_id: int, message: str)`: 
     - Simulates push notification delivery. Logs messages to standard output and logs for validation.

---

## 8. Third-Party Mock Integrations
Two mock integrations are defined:
1. **Mock Payment Escrow (`MockPaymentEscrow` in `app/mock_integrations/payments.py`)**:
   - `initiate_escrow(booking_id: int, customer_id: int, amount: float)`: Simulates locking customer funds in escrow. Returns a unique transaction ID and escrow status `"locked"`.
   - `release_escrow(transaction_id: str)`: Releases escrowed funds to the service provider. Returns escrow status `"released"`.
   - `refund_escrow(transaction_id: str)`: Refunds escrowed funds back to the customer. Returns escrow status `"refunded"`.
2. **Mock SMS Gateway (`MockSMSGateway` in `app/mock_integrations/sms.py`)**:
   - `send_otp(phone_number: str)`: Generates and returns a random 6-digit OTP code, printing it to standard output for testing.
   - `send_sms(phone_number: str, message: str)`: Simulates sending an arbitrary SMS text.

---

## 9. Test Discovery
- **Status**: There are currently **no test files** present in the workspace root `tests/` directory. The `tests/` folder itself has not been initialized.
- **E2E Testing Track**: Our parent agent `sub_orch_e2e` is responsible for building out the E2E testing framework, writing the `TEST_INFRA.md` plan, and implementing Tiers 1-4 tests to verify all specified feature requirements.
