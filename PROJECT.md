# Project: ApnaTask Backend

## Architecture
ApnaTask is a hyperlocal services marketplace backend designed for high-concurrency geospatial location updates, real-time WebSocket bidding, and asynchronous notification tasks.
- **FastAPI Application**: Serves REST APIs and WebSockets.
- **PostgreSQL / PostGIS Database**: Relational storage for customer, provider, and booking requests, with PostGIS for spatial queries.
- **Redis (Spatial index)**: In-memory store for high-frequency location updates (GEOADD/GEORADIUS).
- **Redis (Pub/Sub backplane)**: For clustering WebSocket instances to route negotiation bids across multiple application instances.
- **Celery Engine (RabbitMQ Broker)**: For delayed/background tasks (push notifications, booking expiration timeout).

---

## Code Layout
```
/ (Project Root)
├── .agents/                    # Coordination metadata (no source code here)
├── app/                        # FastAPI application source
│   ├── __init__.py
│   ├── main.py                 # App initialization
│   ├── config.py               # Settings and env loading
│   ├── database.py             # DB connection, models, sessions
│   ├── schemas.py              # Pydantic models
│   ├── routes/                 # Endpoint routers
│   │   ├── __init__.py
│   │   ├── geo.py              # Geospatial location and matching
│   │   └── ws.py               # WebSocket negotiation
│   ├── celery_app.py           # Celery application configuration
│   ├── tasks.py                # Celery background tasks
│   └── mock_integrations/      # Third-party mocks
│       ├── __init__.py
│       ├── payments.py         # Mock EasyPaisa/JazzCash escrow
│       └── sms.py              # Mock SendPK/Jazz Direct OTP
├── migrations/                 # Alembic or SQL migrations
├── tests/                      # Testing directory
│   ├── conftest.py
│   ├── test_geo.py             # Geospatial matching engine tests
│   ├── test_ws.py              # WebSocket bidding tests
│   ├── test_tasks.py           # Async notifications & timeout tests
│   └── test_integrations.py    # Mock integrations tests
├── docker-compose.yml          # Infrastructure orchestrator
├── Dockerfile                  # Application service container configuration
├── requirements.txt            # Python dependencies
└── PROJECT.md                  # Project index (this file)
```

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Base App Setup & Dockerization | Scaffold project structure, write docker-compose.yml for DB/Redis/RabbitMQ/App/Celery, set up FastAPI starter. | None | IN_PROGRESS (sub_orch_impl: 6f1ad6ae-63aa-4556-a313-ebc6e1693c20) |
| M2 | Geospatial Tracking & Matching | Implement Redis location ingestion and PostgreSQL/PostGIS radius/KYC/category filters. | M1 | PLANNED |
| M3 | WebSocket Bidding Server | Implement WebSocket bidding endpoint clustered via Redis Pub/Sub backplane with Mock JWT. | M1 | PLANNED |
| M4 | Celery Task Queue | Implement Celery tasks for booking timeouts (3-min) and push notification triggers. | M1, M3 | PLANNED |
| M5 | Mock Integration Modules | Build EasyPaisa/JazzCash and SMS gateway mocks. | M1 | PLANNED |
| M6 | Final E2E Pass & Hardening | Run opaque-box test suite against app, fix failures, run challenger for Tier 5 hardening. | M2, M3, M4, M5 | PLANNED |

---

## Interface Contracts

### 1. Geospatial tracking and matching:
- `POST /api/v1/provider/location`: Updates a service provider's current location.
  - Request: `{ "provider_id": int, "latitude": float, "longitude": float }`
  - Response: `{ "status": "success" }` (Updates Redis spatial index with GEOADD)
- `GET /api/v1/matching`: Fetches active, verified providers near a customer.
  - Query parameters: `latitude: float`, `longitude: float`, `radius_km: float`, `category: str`
  - Response: `[ { "provider_id": int, "name": str, "latitude": float, "longitude": float, "distance_km": float, "kyc_verified": bool, "category": str } ]`

### 2. WebSocket Negotiation:
- `WS /api/v1/ws/negotiation`: Establish bidding session.
  - Query parameters: `token: str` (Mock JWT token containing `user_id` and `role` - `customer` or `provider`)
  - Subscribes to Redis Pub/Sub channel for the negotiation session (`negotiation_{booking_id}`).
  - Direct message JSON format:
    - Sent/Received: `{ "type": "bid" | "chat" | "accept", "booking_id": int, "sender_id": int, "role": "customer" | "provider", "amount": float, "message": str }`

### 3. Asynchronous Tasks:
- Celery Task: `app.tasks.expire_booking(booking_id: int)`
  - Triggered when booking request is created. Delays for 3 minutes.
  - If status remains "pending" (not accepted), updates booking state to "expired" in DB, and triggers a push notification to user.
- Celery Task: `app.tasks.send_push_notification(user_id: int, message: str)`
  - Simulates sending a push notification (logged to standard output or a mock delivery queue).
