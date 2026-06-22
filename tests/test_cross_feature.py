import pytest
from unittest.mock import patch
from app.database import ProviderModel, BookingModel, SessionLocal
from app.tasks import expire_booking

# Tier 3 Tests: Cross-Feature Combinations

def test_f3_c1_location_matching_booking_expiration(client):
    """Set provider location, run matching, create booking, trigger expire, check status & push."""
    # 1. Seed provider in DB
    db = SessionLocal()
    provider = ProviderModel(name="Saleem", kyc_verified=True, category="Plumbing", phone="+923001234567")
    db.add(provider)
    db.commit()
    provider_id = provider.id
    db.close()

    # 2. Update location
    client.post("/api/v1/provider/location", json={
        "provider_id": provider_id,
        "latitude": 33.6844,
        "longitude": 73.0479
    })

    # 3. Match provider
    match_resp = client.get("/api/v1/matching?latitude=33.6844&longitude=73.0479&radius_km=5.0&category=Plumbing")
    assert len(match_resp.json()) == 1

    # 4. Create booking
    booking_resp = client.post("/api/v1/bookings", json={
        "customer_id": 99,
        "amount": 250.0
    })
    booking_id = booking_resp.json()["id"]

    # 5. Trigger expire booking task & check notification is sent
    with patch("app.tasks.send_push_notification.delay") as mock_notification:
        expire_booking(booking_id)
        mock_notification.assert_called_once_with(99, "customer", "Your booking request has expired.")

    # 6. Verify status updated to expired
    db = SessionLocal()
    booking = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    assert booking.status == "expired"
    db.close()

def test_f3_c2_websocket_negotiation_escrow(client, jwt_helper):
    """Exchange bids over WS, accept, verify it triggers payment escrow."""
    # Seed booking
    db = SessionLocal()
    booking = BookingModel(customer_id=1, amount=300.0, status="pending")
    db.add(booking)
    db.commit()
    booking_id = booking.id
    db.close()

    cust_token = jwt_helper(user_id=1, role="customer")
    prov_token = jwt_helper(user_id=2, role="provider")

    with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id={booking_id}&token={cust_token}") as ws_cust:
        with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id={booking_id}&token={prov_token}") as ws_prov:
            # Setup subscription
            ws_cust.send_json({"type": "chat", "booking_id": booking_id, "sender_id": 1, "role": "customer", "message": "hi"})
            ws_cust.receive_json()
            ws_prov.receive_json()

            # Send bid from customer
            ws_cust.send_json({"type": "bid", "booking_id": booking_id, "sender_id": 1, "role": "customer", "amount": 300.0, "message": "My offer"})
            ws_cust.receive_json()
            ws_prov.receive_json()

            # Accept bid from provider
            ws_prov.send_json({"type": "accept", "booking_id": booking_id, "sender_id": 2, "role": "provider", "amount": 300.0, "message": "Accept bid"})
            
            # Verify customer receives accept containing transaction_id
            recv_msg = ws_cust.receive_json()
            assert recv_msg["type"] == "accept"
            assert "transaction_id" in recv_msg
            assert recv_msg["escrow_status"] == "locked"

            # Check DB state
            db = SessionLocal()
            updated_booking = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
            assert updated_booking.status == "accepted"
            assert updated_booking.provider_id == 2
            assert updated_booking.transaction_id == recv_msg["transaction_id"]
            db.close()

def test_f3_c3_booking_creation_escrow_timeout(client):
    """Create booking, lock funds in escrow, let Celery expire task run on timeout, verify status & refund."""
    # 1. Create booking
    booking_resp = client.post("/api/v1/bookings", json={
        "customer_id": 10,
        "amount": 400.0
    })
    booking_id = booking_resp.json()["id"]

    # 2. Lock funds in escrow
    from app.mock_integrations.payments import MockPaymentEscrow
    escrow_res = MockPaymentEscrow.initiate_escrow(booking_id, 10, 400.0)
    txn_id = escrow_res["transaction_id"]

    db = SessionLocal()
    b = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    b.transaction_id = txn_id
    db.commit()
    db.close()

    # 3. Run Celery expire booking on timeout & check refund was processed
    with patch("app.mock_integrations.payments.MockPaymentEscrow.refund_escrow") as mock_refund:
        expire_booking(booking_id)
        mock_refund.assert_called_once_with(txn_id)

    # 4. Verify DB state is expired
    db = SessionLocal()
    b_updated = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    assert b_updated.status == "expired"
    db.close()

def test_f3_c4_geo_matching_websocket_handshake(client, jwt_helper):
    """Match provider geospatially, extract ID, generate token, and establish WS channel."""
    # Seed provider
    db = SessionLocal()
    provider = ProviderModel(name="Kamran", kyc_verified=True, category="Cleaning", phone="+923001234500")
    db.add(provider)
    db.commit()
    provider_id = provider.id
    db.close()

    # Update location
    client.post("/api/v1/provider/location", json={
        "provider_id": provider_id,
        "latitude": 33.6844,
        "longitude": 73.0479
    })

    # Match provider
    match_resp = client.get("/api/v1/matching?latitude=33.6844&longitude=73.0479&radius_km=5.0&category=Cleaning")
    results = match_resp.json()
    assert len(results) == 1
    matched_provider_id = results[0]["provider_id"]
    assert matched_provider_id == provider_id

    # Generate token and establish WS channel
    token = jwt_helper(user_id=matched_provider_id, role="provider")
    with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id=1&token={token}") as websocket:
        assert websocket is not None

def test_f3_c5_ws_escrow_delivery_notifications(client, jwt_helper):
    """Accept bid over WS -> lock payment -> complete booking -> release escrow -> trigger push notification & SMS OTP."""
    # Seed booking and provider
    db = SessionLocal()
    provider = ProviderModel(name="Naseer", kyc_verified=True, category="Carpentry", phone="+923001234567")
    db.add(provider)
    db.commit()
    provider_id = provider.id

    booking = BookingModel(customer_id=1, amount=1000.0, status="pending")
    db.add(booking)
    db.commit()
    booking_id = booking.id
    db.close()

    cust_token = jwt_helper(user_id=1, role="customer")
    prov_token = jwt_helper(user_id=provider_id, role="provider")

    with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id={booking_id}&token={cust_token}") as ws_cust:
        with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id={booking_id}&token={prov_token}") as ws_prov:
            ws_cust.send_json({"type": "chat", "booking_id": booking_id, "sender_id": 1, "role": "customer", "message": "hey"})
            ws_cust.receive_json()
            ws_prov.receive_json()

            # Accept bid
            ws_prov.send_json({"type": "accept", "booking_id": booking_id, "sender_id": provider_id, "role": "provider", "amount": 1000.0, "message": "deal"})
            recv = ws_cust.receive_json()
            txn_id = recv["transaction_id"]

    # Verify DB has accepted status and transaction_id
    db = SessionLocal()
    booking = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    assert booking.status == "accepted"
    assert booking.transaction_id == txn_id
    db.close()

    # Complete booking via REST endpoint
    with patch("app.mock_integrations.payments.MockPaymentEscrow.release_escrow") as mock_release, \
         patch("app.mock_integrations.sms.MockSMSGateway.send_otp") as mock_otp:
        
        complete_resp = client.post(f"/api/v1/bookings/{booking_id}/complete")
        assert complete_resp.status_code == 200
        mock_release.assert_called_once_with(txn_id)
        mock_otp.assert_called_once_with("+923001234567")

    # Verify status is completed in DB
    db = SessionLocal()
    booking = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    assert booking.status == "completed"
    db.close()


# Tier 4 Tests: Real-World Workflows

def test_f4_w1_happy_path_booking(client, jwt_helper):
    """Complete booking lifecycle: location -> match -> WS bidding & acceptance -> escrow lock -> completion & payout."""
    # 1. Seed provider
    db = SessionLocal()
    provider = ProviderModel(name="Zahid", kyc_verified=True, category="Carpentry", phone="+923001234567")
    db.add(provider)
    db.commit()
    provider_id = provider.id
    db.close()

    # 2. Update coordinates
    client.post("/api/v1/provider/location", json={"provider_id": provider_id, "latitude": 33.6844, "longitude": 73.0479})

    # 3. Customer matches provider
    match_resp = client.get("/api/v1/matching?latitude=33.6844&longitude=73.0479&radius_km=5.0&category=Carpentry")
    results = match_resp.json()
    assert len(results) == 1
    assert results[0]["provider_id"] == provider_id

    # 4. Create booking
    booking_resp = client.post("/api/v1/bookings", json={"customer_id": 50, "amount": 800.0})
    booking_id = booking_resp.json()["id"]

    # 5. WS session created, bidding, acceptance, and escrow lock
    cust_token = jwt_helper(user_id=50, role="customer")
    prov_token = jwt_helper(user_id=provider_id, role="provider")

    with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id={booking_id}&token={cust_token}") as ws_cust:
        with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id={booking_id}&token={prov_token}") as ws_prov:
            ws_cust.send_json({"type": "chat", "booking_id": booking_id, "sender_id": 50, "role": "customer", "message": "ready?"})
            ws_cust.receive_json()
            ws_prov.receive_json()

            ws_prov.send_json({"type": "bid", "booking_id": booking_id, "sender_id": provider_id, "role": "provider", "amount": 850.0, "message": "850 minimum"})
            ws_cust.receive_json()
            ws_prov.receive_json()

            # Customer accepts
            ws_cust.send_json({"type": "accept", "booking_id": booking_id, "sender_id": 50, "role": "customer", "amount": 850.0, "message": "okay"})
            recv = ws_cust.receive_json()
            txn_id = recv["transaction_id"]

    # 6. Provider completes job, escrow released, OTP validation sent
    complete_resp = client.post(f"/api/v1/bookings/{booking_id}/complete")
    assert complete_resp.status_code == 200

    db = SessionLocal()
    b = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    assert b.status == "completed"
    assert b.amount == 850.0
    db.close()

def test_f4_w2_booking_timeout_payout_refund(client):
    """Customer initiates booking. Celery timeout runs (3 mins). Booking expires, customer refunded."""
    # 1. Create booking
    booking_resp = client.post("/api/v1/bookings", json={"customer_id": 60, "amount": 500.0})
    booking_id = booking_resp.json()["id"]

    # 2. Lock funds in escrow
    from app.mock_integrations.payments import MockPaymentEscrow
    escrow_res = MockPaymentEscrow.initiate_escrow(booking_id, 60, 500.0)
    txn_id = escrow_res["transaction_id"]

    db = SessionLocal()
    b = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    b.transaction_id = txn_id
    db.commit()
    db.close()

    # 3. Timeout runs (expire_booking Celery task) and triggers refund
    with patch("app.mock_integrations.payments.MockPaymentEscrow.refund_escrow") as mock_refund:
        expire_booking(booking_id)
        mock_refund.assert_called_once_with(txn_id)

    # 4. Check DB status
    db = SessionLocal()
    b_after = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    assert b_after.status == "expired"
    db.close()

def test_f4_w3_provider_verification_filtering(client, jwt_helper):
    """Multi-provider updates (one KYC-verified, one not). Matching engine filters out unverified. Connect WS -> Booking expires."""
    # 1. Seed two providers: p1 (KYC verified), p2 (Not KYC verified)
    db = SessionLocal()
    p1 = ProviderModel(name="Verified Prov", kyc_verified=True, category="Plumbing", phone="+923001234501")
    p2 = ProviderModel(name="Unverified Prov", kyc_verified=False, category="Plumbing", phone="+923001234502")
    db.add(p1)
    db.add(p2)
    db.commit()
    p1_id, p2_id = p1.id, p2.id
    db.close()

    # 2. Update coordinates
    client.post("/api/v1/provider/location", json={"provider_id": p1_id, "latitude": 33.6844, "longitude": 73.0479})
    client.post("/api/v1/provider/location", json={"provider_id": p2_id, "latitude": 33.6844, "longitude": 73.0479})

    # 3. Matching filters out p2 (unverified)
    match_resp = client.get("/api/v1/matching?latitude=33.6844&longitude=73.0479&radius_km=5.0&category=Plumbing")
    results = match_resp.json()
    assert len(results) == 1
    assert results[0]["provider_id"] == p1_id

    # 4. Create booking
    booking_resp = client.post("/api/v1/bookings", json={"customer_id": 70, "amount": 300.0})
    booking_id = booking_resp.json()["id"]

    # 5. Connect WS, client disconnects before accept, booking expires naturally
    cust_token = jwt_helper(user_id=70, role="customer")
    with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id={booking_id}&token={cust_token}") as ws:
        ws.send_json({"type": "chat", "booking_id": booking_id, "sender_id": 70, "role": "customer", "message": "is anyone there?"})
        ws.receive_json()

    # 6. Booking expires naturally
    expire_booking(booking_id)
    db = SessionLocal()
    b = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    assert b.status == "expired"
    db.close()

def test_f4_w4_bid_war_negotiation(client, jwt_helper):
    """Customer and multiple providers connect to same WebSocket. Providers bid against each other. Customer accepts lowest bid."""
    # Seed 2 providers
    db = SessionLocal()
    p1 = ProviderModel(name="Provider A", kyc_verified=True, category="Plumbing", phone="+923001234501")
    p2 = ProviderModel(name="Provider B", kyc_verified=True, category="Plumbing", phone="+923001234502")
    db.add(p1)
    db.add(p2)
    db.commit()
    p1_id, p2_id = p1.id, p2.id
    
    # Seed booking
    booking = BookingModel(customer_id=15, amount=500.0, status="pending")
    db.add(booking)
    db.commit()
    booking_id = booking.id
    db.close()

    cust_token = jwt_helper(user_id=15, role="customer")
    p1_token = jwt_helper(user_id=p1_id, role="provider")
    p2_token = jwt_helper(user_id=p2_id, role="provider")

    with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id={booking_id}&token={cust_token}") as ws_cust:
        with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id={booking_id}&token={p1_token}") as ws_p1:
            with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id={booking_id}&token={p2_token}") as ws_p2:
                # Initialize subscriptions
                ws_cust.send_json({"type": "chat", "booking_id": booking_id, "sender_id": 15, "role": "customer", "message": "Need a leak fixed"})
                ws_cust.receive_json()
                ws_p1.receive_json()
                ws_p2.receive_json()

                # Provider A bids 480
                ws_p1.send_json({"type": "bid", "booking_id": booking_id, "sender_id": p1_id, "role": "provider", "amount": 480.0, "message": "I can do 480"})
                ws_cust.receive_json()
                ws_p1.receive_json()
                ws_p2.receive_json()

                # Provider B bids 450
                ws_p2.send_json({"type": "bid", "booking_id": booking_id, "sender_id": p2_id, "role": "provider", "amount": 450.0, "message": "I can do 450"})
                ws_cust.receive_json()
                ws_p1.receive_json()
                ws_p2.receive_json()

                # Customer accepts lowest bid (450)
                ws_cust.send_json({"type": "accept", "booking_id": booking_id, "sender_id": 15, "role": "customer", "amount": 450.0, "message": "Accepting B at 450"})
                recv = ws_cust.receive_json()
                assert recv["type"] == "accept"
                txn_id = recv["transaction_id"]
                assert recv["amount"] == 450.0

    # Payout validation on completion
    complete_resp = client.post(f"/api/v1/bookings/{booking_id}/complete")
    assert complete_resp.status_code == 200

    with SessionLocal() as db:
        b = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
        assert b.status == "completed"
        assert b.amount == 450.0
        assert b.provider_id == p2_id

def test_f4_w5_canceled_booking_refund(client, jwt_helper):
    """Customer books provider and locks payment. Before accept, customer cancels booking. Escrow refunded and SMS sent."""
    # Seed booking
    db = SessionLocal()
    booking = BookingModel(customer_id=1, amount=600.0, status="pending", customer_phone="+923001234567")
    db.add(booking)
    db.commit()
    booking_id = booking.id
    db.close()

    cust_token = jwt_helper(user_id=1, role="customer")
    prov_token = jwt_helper(user_id=2, role="provider")

    with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id={booking_id}&token={cust_token}") as ws_cust:
        with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id={booking_id}&token={prov_token}") as ws_prov:
            ws_cust.send_json({"type": "chat", "booking_id": booking_id, "sender_id": 1, "role": "customer", "message": "hi"})
            ws_cust.receive_json()
            ws_prov.receive_json()

            # Accept bid (which locks payment)
            ws_prov.send_json({"type": "accept", "booking_id": booking_id, "sender_id": 2, "role": "provider", "amount": 600.0, "message": "accepting"})
            recv = ws_cust.receive_json()
            txn_id = recv["transaction_id"]

    # Customer cancels booking before further progress
    with patch("app.mock_integrations.payments.MockPaymentEscrow.refund_escrow") as mock_refund, \
         patch("app.mock_integrations.sms.MockSMSGateway.send_sms") as mock_sms:
        
        cancel_resp = client.post(f"/api/v1/bookings/{booking_id}/cancel")
        assert cancel_resp.status_code == 200
        mock_refund.assert_called_once_with(txn_id)
        mock_sms.assert_called_once_with("+923001234567", f"Booking {booking_id} canceled. Refund processed.")

    # Check state is canceled in DB
    db = SessionLocal()
    b = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    assert b.status == "canceled"
    db.close()
