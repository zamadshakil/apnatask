# Plan — ApnaTask Backend Implementation

## Objective
Drive the ApnaTask backend implementation project to completion. Formulate and execute a dual-track strategy containing:
1. An independent **E2E Testing Track** producing an opaque-box, requirement-driven test suite (Tiers 1-4) and publishing `TEST_READY.md`.
2. An **Implementation Track** building the backend services across 5 milestone stages, culminating in a final Milestone 6 which passes 100% E2E tests and goes through Tier 5 adversarial hardening.

---

## Track 1: E2E Testing Track Plan

This track designs the E2E test suite from requirements (`ORIGINAL_REQUEST.md`), independently of the codebase implementation, verifying endpoints as black boxes.

### Test Architecture
- **Language/Framework**: Python with `pytest` and `websockets`/`httpx` clients.
- **Tiers**:
  - **Tier 1 (Feature Coverage)**: At least 5 test cases per feature. Features: Geospatial tracking & matching (F1), WS Bidding (F2), Async Notification & Expiration (F3), Mock Integrations (F4).
  - **Tier 2 (Boundary & Corner Cases)**: At least 5 edge cases per feature (e.g., negative coordinates, zero-radius, non-existent customer, expired tokens, Celery execution timing, empty/extreme inputs).
  - **Tier 3 (Cross-Feature Pairwise)**: Combinations such as location updates happening concurrently with a live bid negotiation, or bid expiration triggering alerts while WS is connected.
  - **Tier 4 (Real-World Application Scenarios)**: End-to-end user workflows (e.g. Customer requests matching, sends a bid, provider counter-bids via WS, customer accepts escrow wallet payment, Celery worker handles completion/commissions, notification sent via SMS).
- **Execution**: E2E tests will run against docker-compose services.

### Milestones for Testing Track
- **M_TEST_INFRA**: Design `TEST_INFRA.md` and scaffold test runner/environment.
- **M_TEST_TIERS**: Implement Tier 1, 2, 3, and 4 test cases. Publish `TEST_READY.md`.

---

## Track 2: Implementation Track Plan

This track builds the core services of ApnaTask in a modular, clean, and decoupled fashion.

### Milestones for Implementation Track
- **M1: Base App Setup & Dockerization**
  - Create directory layout.
  - Write `docker-compose.yml` defining PostgreSQL (with PostGIS), Redis, RabbitMQ, and app/worker containers.
  - Set up FastAPI app entry points, configuration, and migrations runner.
- **M2: Geospatial Tracking & Matching Engine (R1)**
  - Implement location ingestion endpoint (`POST /provider/location`) storing coordinates in Redis spatial index (GEOADD).
  - Implement matching endpoint (`GET /matching`) querying Redis for providers in radius, then querying PostgreSQL/PostGIS to filter by category, KYC status, and availability.
- **M3: Real-Time WebSocket Bidding Server (R2)**
  - Create WebSocket endpoints (`/ws/negotiation`) accepting mock JWT tokens (containing role/user ID).
  - Use Redis Pub/Sub to cluster WebSocket connections across stateless server instances.
  - Implement real-time bid, counter-bid, and chat routing between customer and provider.
- **M4: Asynchronous Notification & Task Queue (R3)**
  - Set up Celery worker container.
  - Implement task to send push notification alert when a bid/quote is received.
  - Implement task to automatically expire booking requests after 3 minutes if not accepted.
- **M5: Mocked Integration Modules (R4)**
  - Build clean interface package for payment gateway (EasyPaisa/JazzCash) for escrows/commissions.
  - Build clean interface package for SMS gateways (SendPK/Jazz Direct) for OTPs.
- **M6: E2E Pass & Adversarial Hardening (Tier 5)**
  - Phase 1: Integrate E2E test suite from `TEST_READY.md`. Fix bugs until all Tier 1-4 tests pass.
  - Phase 2: Adversarial Coverage Hardening (Tier 5). Challenger analyzes codebase/tests to find gaps and write adversarial test cases. Iterate until no gaps remain.

---

## Verification & Integrity Gates

For each milestone, the orchestrator will:
1. Dispatch work to subagents.
2. Verify results using Reviewer (correctness, clean code), Challenger (robustness, stress-testing), and Forensic Auditor (authenticity, no cheating).
3. Ensure no integrity violations exist (hard veto by Auditor).
