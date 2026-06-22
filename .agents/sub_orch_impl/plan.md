# Implementation Plan: ApnaTask Backend

## Objective
Drive the sequential implementation and verification of milestones M1 through M6.

## Verification Protocol (for each milestone)
1. **Explorer Phase**: Spawn 3 Explorer agents to analyze current status, requirements, and layout, and propose a detailed design/implementation plan.
2. **Worker Phase**: Spawn 1 Worker agent with code integrity instructions. Worker implements code, tests, configuration, runs builds/tests, and provides verification output.
3. **Reviewer Phase**: Spawn 2 Reviewer agents to independently review the code changes and verify tests.
4. **Challenger Phase**: Spawn 2 Challenger agents to empirically verify robustness, edge cases, and compliance.
5. **Auditor Phase**: Spawn 1 Forensic Auditor agent to perform integrity verification (no hardcoding, no dummy/facade code, clean code implementation).
6. **Gate Check**: If auditor verdict is clean, tests pass, no reviewer vetoes, and challenger confirms correctness -> Mark done. Otherwise, loop back.

## Milestone Schedule
- **M1: Base App Setup & Dockerization**
  - Goals: Scaffold project structure, create requirements.txt, Dockerfile, docker-compose.yml (Postgres/PostGIS, Redis, RabbitMQ, FastAPI app, Celery worker), and basic FastAPI app initialization (health check and status).
  - Target files: `app/main.py`, `app/config.py`, `app/database.py`, `app/__init__.py`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`.
- **M2: Geospatial Tracking & Matching Engine (R1)**
  - Goals: PostGIS setup, location updates ingestion in Redis (GEOADD), matching query in PostgreSQL/PostGIS (radius search, KYC check, category filter).
  - Target files: `app/routes/geo.py`, `app/schemas.py`, tests for geospatial matching.
- **M3: WebSocket Bidding Server (R2)**
  - Goals: WS endpoint for bidding, Redis pub/sub backplane for bid propagation, mock JWT authentication.
  - Target files: `app/routes/ws.py`, ws connection manager, tests.
- **M4: Asynchronous Notification & Task Queue (R3)**
  - Goals: Celery task integration. Expiration timeout task (3 minutes) update booking status, push notifications task simulation.
  - Target files: `app/tasks.py`, `app/celery_app.py`, tests.
- **M5: Mocked Integration Modules (R4)**
  - Goals: EasyPaisa/JazzCash mock endpoints, SMS gateway mock.
  - Target files: `app/mock_integrations/payments.py`, `app/mock_integrations/sms.py`, tests.
- **M6: E2E Integration (Phase 1) & Adversarial Hardening (Phase 2)**
  - Phase 1: Wait for E2E tests ready signal, pass all tests.
  - Phase 2: Inverted cycle (Challengers find gaps -> Worker fixes -> Reviewer verifies) to harden coverage.
