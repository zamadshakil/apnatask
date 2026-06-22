# TEST_INFRA — E2E Test Suite Specification

## Test Philosophy
- **Opaque-Box**: The test suite exercises the ApnaTask application strictly through its external API routes (REST, WebSockets), background tasks (Celery queue), and mock external gateways. It does not inspect database tables directly except to verify end-state persistence, and does not require knowledge of internal routing or helper class implementation.
- **Requirement-Driven**: Tests are designed directly from the functional contracts specified in `PROJECT.md`.
- **Methodology**: Uses standard Python unit-test framework (`pytest` + `pytest-asyncio`) leveraging FastAPI's `TestClient` for HTTP/WebSocket verification, custom client hooks, and the Celery test runner.

## Feature Inventory
- **F1: Geospatial Tracking & Matching**: High-speed provider location ingestion (`POST /api/v1/provider/location`) and matching engine filtering (`GET /api/v1/matching`).
- **F2: WebSocket Bidding**: Stateful negotiation channel (`WS /api/v1/ws/negotiation`) connecting customer and provider using mock JWT authentication.
- **F3: Async Queue**: Background task engine processing Celery tasks for booking timeouts (`expire_booking`) and notifications (`send_push_notification`).
- **F4: Mock Integrations**: Mock third-party escrow payment processing and SMS OTP gateway operations.

## Test Architecture
- **Environment**: FastAPI app test instance with an isolated database session (rolled back after each test).
- **Redis Mocking / Isolated Redis**: Connection overrides to a dedicated testing Redis database/key namespace to prevent pollution.
- **Celery Test Mode**: Tests utilize Celery's `task_always_eager` mode, allowing task execution to happen synchronously inline, or a local test worker depending on the scope.
- **Mock JWT Helper**: Standard helper inside `tests/conftest.py` to sign mock JWTs containing client info (User ID, Role).

---

## Test Cases Inventory

### Tier 1: Feature Coverage (20 tests)

#### F1: Geospatial Ingestion & Matching
- **test_f1_t1_location_update_success**: Ingest valid coordinates for a provider and verify `200 OK` status and `"success"` body.
- **test_f1_t1_matching_empty**: Query matching engine with no active providers in the area and verify it returns an empty list `[]`.
- **test_f1_t1_matching_results**: Ingest coordinates for a provider, query matching engine within radius, and verify it returns the provider.
- **test_f1_t1_matching_distance_calculation**: Ingest provider coordinates at a known distance from target, verify returned distance matches mathematical distance.
- **test_f1_t1_matching_category_filter**: Ingest providers with different categories, match near location, and check that filtering by category works.

#### F2: WebSocket Bidding
- **test_f2_t1_ws_connect_customer**: Connect customer WS using valid mock token, verify connection is accepted.
- **test_f2_t1_ws_connect_provider**: Connect provider WS using valid mock token, verify connection is accepted.
- **test_f2_t1_ws_bid_message_exchange**: Connect customer and provider, send a bid JSON message from customer, check that both receive it.
- **test_f2_t1_ws_accept_message_exchange**: Send an `"accept"` message JSON from provider, check that customer receives it.
- **test_f2_t1_ws_chat_message_exchange**: Send a `"chat"` message JSON between participants and verify delivery.

#### F3: Async Queue
- **test_f3_t1_expire_booking_trigger**: Call `expire_booking` task synchronously and check returned dictionary status.
- **test_f3_t1_expire_booking_pending**: Verify that running `expire_booking` on a booking with `"pending"` state changes its status to `"expired"`.
- **test_f3_t1_expire_booking_accepted**: Verify that running `expire_booking` on an `"accepted"` booking does NOT change its status.
- **test_f3_t1_send_push_notification_logging**: Run `send_push_notification` task, verify task output matches message.
- **test_f3_t1_expire_booking_calls_notification**: Run `expire_booking` and check that it schedules a push notification.

#### F4: Mock Integrations
- **test_f4_t1_initiate_escrow_success**: Call payment escrow initiation, check transaction ID returned and status `"locked"`.
- **test_f4_t1_release_escrow_success**: Call release escrow for locked transaction, check status becomes `"released"`.
- **test_f4_t1_refund_escrow_success**: Call refund escrow for transaction, check status becomes `"refunded"`.
- **test_f4_t1_send_otp_code**: Send SMS OTP code, check that a 6-digit OTP code is returned.
- **test_f4_t1_send_sms_success**: Send arbitrary SMS text, check that MockSMSGateway returns `True`.

---

### Tier 2: Boundary & Corner Cases (20 tests)

#### F1: Geospatial Ingestion & Matching
- **test_f1_t2_lat_out_of_bounds_low**: Submit provider latitude -90.1, check it raises Pydantic/HTTP 422 error.
- **test_f1_t2_lat_out_of_bounds_high**: Submit provider latitude 90.1, check it raises Pydantic/HTTP 422 error.
- **test_f1_t2_lon_out_of_bounds_low**: Submit provider longitude -180.1, check it raises Pydantic/HTTP 422 error.
- **test_f1_t2_lon_out_of_bounds_high**: Submit provider longitude 180.1, check it raises Pydantic/HTTP 422 error.
- **test_f1_t2_invalid_radius**: Submit matching request with radius <= 0, check it raises validation error.

#### F2: WebSocket Bidding
- **test_f2_t2_ws_invalid_token**: Attempt connection with invalid token format, verify connection closed or HTTP 403/401/422.
- **test_f2_t2_ws_missing_token**: Attempt connection without token, verify connection rejected with 422.
- **test_f2_t2_ws_malformed_json**: Send malformed JSON structure to WS, verify system handles it without crashing.
- **test_f2_t2_ws_missing_message_fields**: Send WS JSON missing `booking_id` or `role`, check that validator rejects message.
- **test_f2_t2_ws_invalid_sender_role**: Connect with a token containing role `"guest"` or invalid fields, check connection rejection.

#### F3: Async Queue
- **test_f3_t2_expire_booking_nonexistent**: Run `expire_booking` on a non-existent booking ID, check that it handles the database query exception.
- **test_f3_t2_send_push_negative_id**: Call `send_push_notification` with user_id <= 0, check error logs/validation.
- **test_f3_t2_task_soft_time_limit**: Force Celery worker soft time limit exception and ensure it is trapped.
- **test_f3_t2_db_retry_on_failure**: Simulate DB database lock error during `expire_booking` and check that Celery retries the task.
- **test_f3_t2_worker_log_capture**: Ensure logger outputs appropriate warning when booking status is already processed.

#### F4: Mock Integrations
- **test_f4_t2_escrow_empty_txn_id**: Call release escrow with empty transaction ID, verify it raises ValueError or handles error.
- **test_f4_t2_escrow_refund_empty_txn_id**: Call refund escrow with empty transaction ID, verify error is raised.
- **test_f4_t2_sms_invalid_phone_format**: Try sending SMS to an invalid phone number format, verify gateway raises ValueError.
- **test_f4_t2_escrow_negative_amount**: Try initiating escrow with amount <= 0, verify it is rejected.
- **test_f4_t2_send_otp_empty_phone**: Request OTP with empty phone number string, verify it raises ValueError.

---

### Tier 3: Cross-Feature Combinations (5 tests)
- **test_f3_c1_location_matching_booking_expiration**: Set provider location, run matching, create booking request, trigger Celery expire task, check status becomes expired and push notification is triggered.
- **test_f3_c2_websocket_negotiation_escrow**: Establish customer/provider WS channels, exchange bids, send accept, and check that accepting bid triggers mock escrow payment gateway.
- **test_f3_c3_booking_creation_escrow_timeout**: Create booking, lock funds in escrow, let Celery expire task run on timeout, verify status updates to expired and funds are automatically refunded.
- **test_f3_c4_geo_matching_websocket_handshake**: Match provider geospatially, extract ID, generate token, and successfully establish WS channel for the session.
- **test_f3_c5_ws_escrow_delivery_notifications**: Accept bid over WS -> lock payment escrow -> complete booking -> release escrow -> trigger push notification + OTP message to verify provider payout.

---

### Tier 4: Real-World Workflows (5 tests)
- **test_f4_w1_happy_path_booking**: Complete booking lifecycle: Provider coordinates updated. Customer matches provider. WS session created. Bids negotiated and accepted. Escrow payment locked. Provider completes job, escrow released. SMS OTP validation sent.
- **test_f4_w2_booking_timeout_payout_refund**: Customer initiates booking. Celery timeout runs (3 mins). No provider accepts booking. Celery updates DB status to `"expired"`. Push notification sent to customer. Mock Escrow refunds customer.
- **test_f4_w3_provider_verification_filtering**: Multi-provider location updates (some KYC-verified, some not). Matching engine filters out unverified provider. Customer matches verified provider, begins WS negotiation, client disconnects before accept, booking expires naturally.
- **test_f4_w4_bid_war_negotiation**: Customer and multiple providers connect to same WebSocket booking channel. Providers bid against each other. Customer accepts lowest bid. Mock payment locks that amount. Payout is processed on completion.
- **test_f4_w5_canceled_booking_refund**: Customer books provider and locks payment. Before bid is accepted, customer cancels booking. FastAPI endpoint receives cancel, updates state in DB, Celery cancellation check refunds escrow and sends SMS cancellation alert.
