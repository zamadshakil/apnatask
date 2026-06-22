## 2026-06-22T21:02:33Z
You are the E2E Codebase & Test Suite Explorer for ApnaTask.
Your working directory is: E:\Zamad's Personal Agents Squad\apnatask\.agents\explorer_e2e_1
Your mission:
1. Inspect the existing test suite in `tests/` (`conftest.py`, `test_geo.py`, `test_ws.py`, `test_tasks.py`, `test_integrations.py`, `test_cross_feature.py`).
2. Verify if docker-compose is currently running on the system, and determine if the database, Redis, RabbitMQ, and FastAPI app are properly started.
3. Discover how Celery tasks are run in the project, and how the test suite can trigger and verify their side effects against the actual docker-compose infrastructure without mocking.
4. Formulate a detailed strategy to refactor/rewrite the test suite so that it runs against the actual docker-compose infrastructure (e.g. REST API, WebSocket negotiation, Celery queue) without mock-patching the database, Redis, or Celery.
5. Identify any missing test coverage or features that need to be scaffolded to fulfill Tiers 1-4 with at least 49 tests.
Write your analysis to `E:\Zamad's Personal Agents Squad\apnatask\.agents\explorer_e2e_1\analysis.md` and a handoff to `E:\Zamad's Personal Agents Squad\apnatask\.agents\explorer_e2e_1\handoff.md`.
