# Original User Request

## Initial Request — 2026-06-21T17:10:20Z

Build the core backend services for ApnaTask, a scalable, trust-first hyperlocal services marketplace. The backend must be designed to handle high-concurrency geospatial location updates, real-time bid negotiations, and asynchronous notifications.

Working directory: E:/Zamad's Personal Agents Squad/apnatask
Integrity mode: benchmark

## Requirements

### R1. Geospatial Tracking & Matching Engine
- Implement a location ingestion API that receives frequent coordinate updates from service providers and stores them in an in-memory spatial index (Redis).
- Implement a matching endpoint that queries the active providers in Redis, filters them by a configurable geographical radius, and cross-references PostgreSQL (using PostGIS or relational queries) to filter by provider status, verification (KYC), and category.

### R2. Real-Time WebSocket Bidding Server
- Create a stateless WebSocket communication server that allows customers and service providers to connect, authenticate (using mock JWT tokens), and engage in live negotiation chat.
- Use a Redis Pub/Sub backplane to cluster WebSocket connections, ensuring a message sent to a customer on Server A is correctly routed to a provider on Server B.

### R3. Asynchronous Notification & Task Queue
- Implement a Celery-based task worker queue using Redis/RabbitMQ as the message broker.
- Create automated background tasks for:
  - Sending push notification alerts when a new quote/bid is received.
  - Automatically expiring booking requests after a 3-minute timeout if no provider accepts the bid.

### R4. Mocked Integration Modules
- Build clean, decoupled interface packages for:
  - Payments (EasyPaisa/JazzCash) for processing virtual wallet escrows and commission cuts.
  - SMS Gateways (SendPK/Jazz Direct) for OTP dispatching and registration security.

## Verification & Acceptance Criteria

### Infrastructure & Execution
- The working directory must contain a `docker-compose.yml` file to spin up PostgreSQL (with PostGIS), Redis, RabbitMQ, and the application services.

### Geospatial Matching Verification
- An integration test must simulate 50 active providers updating their locations. A customer search query must return the subset of active, verified providers within the correct radius in under 150ms.

### WebSocket Bidding Verification
- An integration test must establish concurrent WebSocket connections simulating a customer and a provider, submit a bid, submit a counter-bid, and verify that both clients receive the correct real-time updates.

### Async Task Verification
- An integration test must verify that launching a booking request triggers a delayed Celery task that successfully executes and marks the request as "expired" if not accepted within the timeout window.

## Follow-up — 2026-06-21T20:29:20Z

Hi! Can you report your current progress on the ApnaTask backend service milestones? We want to ensure all endpoints and tests are fully passing.
