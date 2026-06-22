# E2E Test Suite Implementation Plan

## Phase 1: Codebase & Infrastructure Discovery
1. Spawn an Explorer subagent to inspect the existing files, docker-compose, FastAPI app entry point, configuration, db models, Celery config, and existing tests in `apnatask`.
2. Analyze the requirements for features:
   - F1: Geospatial tracking & matching (FastAPI routes, Redis spatial index, PostGIS/DB queries)
   - F2: WS Bidding (WebSocket negotiation endpoint, Redis Pub/Sub, client/provider roles, mock JWT)
   - F3: Async Queue (Celery tasks for booking timeouts and push notifications)
   - F4: Mock Integrations (EasyPaisa/JazzCash mock escrow, SMS OTP mock gateway)

## Phase 2: Design and Define TEST_INFRA.md
1. Write `E:\Zamad's Personal Agents Squad\apnatask\TEST_INFRA.md` detailing:
   - Test Philosophy: requirement-driven, opaque-box, independent of internals.
   - Feature Inventory: F1-F4.
   - Test Architecture: FastAPI TestClient, WebSocket client helpers, mock DB/Redis/Celery testing strategies.
   - Design at least 49 test cases covering:
     - Tier 1: Feature Coverage (>=5 per feature = 20 tests)
     - Tier 2: Boundary & Edge cases (>=5 per feature = 20 tests)
     - Tier 3: Cross-Feature Combinations (pairwise, >=4 tests)
     - Tier 4: Real-world scenarios (>=5 workflows)

## Phase 3: Scaffolding and Implementation
1. Spawn a Worker subagent to:
   - Scaffold the test environment: create/update `tests/conftest.py` with necessary fixtures (test db, test redis, Celery eager/worker setup, mock JWT token helper, HTTP clients).
   - Write Tier 1 tests (Feature Coverage).
   - Write Tier 2 tests (Boundary & Corner Cases).
   - Write Tier 3 tests (Cross-Feature Combinations).
   - Write Tier 4 tests (Real-World Application Scenarios).
   All tests must follow opaque-box API call conventions and assert correct status codes, body response schemas, WebSocket bid responses, Celery tasks execution side-effects, and mock integration logs/callbacks.

## Phase 4: Review and Validation
1. Spawn Reviewer subagent to audit the test code structure, logic correctness, and robustness.
2. Spawn Challenger subagent to run the test suite (via pytest), ensure 100% test pass, and generate coverage report.
3. Spawn Forensic Auditor to verify that tests are genuine, do not hardcode expected test data to bypass logic, and maintain high codebase integrity.

## Phase 5: Handoff and Completion
1. Address any review/challenger/auditor findings.
2. Write `E:\Zamad's Personal Agents Squad\apnatask\TEST_READY.md` containing the E2E Test Suite coverage checklist.
3. Update `progress.md` and `BRIEFING.md`.
4. Send completion message to parent.
