## 2026-06-21T17:15:50Z
You are a Worker subagent for ApnaTask backend E2E testing track.
Working directory: E:\Zamad's Personal Agents Squad\apnatask\.agents\teamwork_preview_worker_m1
Parent: sub_orch_e2e

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Mission:
Implement the complete E2E test suite in the `tests/` directory at the project root (`E:\Zamad's Personal Agents Squad\apnatask\tests`).
You must design and implement the 50 test cases specified in the `TEST_INFRA.md` file:
1. `tests/conftest.py`: Base fixtures, mock DB connections, mock Redis client, mock Celery client, mock JWT creation helper, FastAPI TestClient.
2. `tests/test_geo.py`: Tier 1 & Tier 2 tests for Geospatial Location Updates and Matching.
3. `tests/test_ws.py`: Tier 1 & Tier 2 tests for WebSocket negotiation and message exchanges.
4. `tests/test_tasks.py`: Tier 1 & Tier 2 tests for Celery tasks (`expire_booking` and `send_push_notification`).
5. `tests/test_integrations.py`: Tier 1 & Tier 2 tests for Payment Escrow and SMS Gateway mocks.
6. Tier 3 (Cross-Feature Combinations) and Tier 4 (Real-world workflows) test cases distributed appropriately across the test files or in separate files (e.g. `tests/test_cross_feature.py` or within the main test modules).

Since Docker/external services (PostgreSQL/PostGIS, Redis, RabbitMQ) are not running on the machine, you must implement the test environment in `conftest.py` using robust, clean mocks (e.g., standard unittest mock, mock DB session overrides, mock Redis client with spatial and Pub/Sub mock commands, mock Celery task runners) to guarantee that all 50 test cases execute and pass 100% when running `pytest` locally, without requiring real databases.

Wait, check the proposed implementation files in `E:\Zamad's Personal Agents Squad\apnatask\.agents\explorer_m1_3\`:
- `proposed_main.py`
- `proposed_routes_geo.py`
- `proposed_routes_ws.py`
- `proposed_tasks.py`
- `proposed_mock_payments.py`
- `proposed_mock_sms.py`
Make sure your E2E tests are designed to call the FastAPI app (`app`) and modules as imported from `app.main`, `app.routes.geo`, etc., according to the structure specified in `PROJECT.md`.

Once written, verify and run the tests. Document your work and output in your handoff report (`handoff.md` in your working directory) and update your `progress.md`. Send a message back to the parent indicating completion.
