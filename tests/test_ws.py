import pytest
from starlette.testclient import WebSocketDisconnect
from app.database import BookingModel, SessionLocal

# Tier 1 Tests: WebSocket Negotiation

def test_f2_t1_ws_connect_customer(client, jwt_helper):
    """Connect customer WS using valid mock token and verify connection is accepted."""
    token = jwt_helper(user_id=1, role="customer")
    with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id=1&token={token}") as websocket:
        assert websocket is not None

def test_f2_t1_ws_connect_provider(client, jwt_helper):
    """Connect provider WS using valid mock token and verify connection is accepted."""
    token = jwt_helper(user_id=2, role="provider")
    with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id=1&token={token}") as websocket:
        assert websocket is not None

def test_f2_t1_ws_bid_message_exchange(client, jwt_helper):
    """Connect customer and provider, send a bid message, and check both receive it."""
    cust_token = jwt_helper(user_id=1, role="customer")
    prov_token = jwt_helper(user_id=2, role="provider")
    
    # Connect both
    with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id=1&token={cust_token}") as ws_cust:
        with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id=1&token={prov_token}") as ws_prov:
            
            # Send message from customer
            bid_msg = {
                "type": "bid",
                "booking_id": 1,
                "sender_id": 1,
                "role": "customer",
                "amount": 150.0,
                "message": "My first bid"
            }
            ws_cust.send_json(bid_msg)
            
            # Receive on both
            cust_recv = ws_cust.receive_json()
            prov_recv = ws_prov.receive_json()
            
            assert cust_recv["amount"] == 150.0
            assert prov_recv["amount"] == 150.0
            assert cust_recv["type"] == "bid"

def test_f2_t1_ws_accept_message_exchange(client, jwt_helper):
    """Send an 'accept' message from provider, and check that customer receives it."""
    # Seed booking so accept logic has a booking to update in DB
    db = SessionLocal()
    booking = BookingModel(customer_id=10, amount=200.0, status="pending")
    db.add(booking)
    db.commit()
    booking_id = booking.id
    db.close()

    cust_token = jwt_helper(user_id=10, role="customer")
    prov_token = jwt_helper(user_id=20, role="provider")
    
    with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id={booking_id}&token={cust_token}") as ws_cust:
        with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id={booking_id}&token={prov_token}") as ws_prov:
            
            # Provider sends accept
            accept_msg = {
                "type": "accept",
                "booking_id": booking_id,
                "sender_id": 20,
                "role": "provider",
                "amount": 200.0,
                "message": "Accepted booking"
            }
            ws_prov.send_json(accept_msg)
            
            # Customer receives accepted broadcast
            cust_recv = ws_cust.receive_json()
            assert cust_recv["type"] == "accept"
            assert cust_recv["booking_id"] == booking_id
            assert "transaction_id" in cust_recv

def test_f2_t1_ws_chat_message_exchange(client, jwt_helper):
    """Send a chat message between participants and verify delivery."""
    cust_token = jwt_helper(user_id=1, role="customer")
    prov_token = jwt_helper(user_id=2, role="provider")
    
    with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id=5&token={cust_token}") as ws_cust:
        with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id=5&token={prov_token}") as ws_prov:
            
            chat_msg = {
                "type": "chat",
                "booking_id": 5,
                "sender_id": 2,
                "role": "provider",
                "message": "Can you share exact location?"
            }
            ws_prov.send_json(chat_msg)
            
            cust_recv = ws_cust.receive_json()
            assert cust_recv["type"] == "chat"
            assert cust_recv["message"] == "Can you share exact location?"


# Tier 2 Tests: Boundary & Corner Cases

def test_f2_t2_ws_invalid_token(client):
    """Attempt connection with invalid token format, verify connection closed or HTTP 403."""
    # Connecting with invalid token should throw 403
    response = client.get("/api/v1/ws/negotiation?booking_id=1&token=bad-token")
    assert response.status_code == 403

def test_f2_t2_ws_missing_token(client):
    """Attempt connection without token, verify connection rejected with 422."""
    response = client.get("/api/v1/ws/negotiation?booking_id=1")
    assert response.status_code == 422

def test_f2_t2_ws_malformed_json(client, jwt_helper):
    """Send malformed JSON to WS, verify system handles it without crashing."""
    token = jwt_helper(user_id=1, role="customer")
    with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id=1&token={token}") as ws:
        # Send raw malformed string
        ws.send_text("this is not json")
        # System should respond with error JSON without disconnecting
        resp = ws.receive_json()
        assert "error" in resp
        assert resp["error"] == "Malformed JSON"
        
        # Send valid JSON now to verify it is still alive
        ws.send_json({
            "type": "chat",
            "booking_id": 1,
            "sender_id": 1,
            "role": "customer",
            "message": "still here"
        })
        resp2 = ws.receive_json()
        assert resp2["message"] == "still here"

def test_f2_t2_ws_missing_message_fields(client, jwt_helper):
    """Send WS JSON missing booking_id or role, check that validator rejects message."""
    token = jwt_helper(user_id=1, role="customer")
    with client.websocket_connect(f"/api/v1/ws/negotiation?booking_id=1&token={token}") as ws:
        # Missing booking_id
        ws.send_json({
            "type": "chat",
            "sender_id": 1,
            "role": "customer",
            "message": "missing fields"
        })
        resp = ws.receive_json()
        assert "error" in resp
        assert resp["error"] == "Missing message fields"

def test_f2_t2_ws_invalid_sender_role(client, jwt_helper):
    """Connect with a token containing role 'guest', check connection rejection."""
    token = jwt_helper(user_id=1, role="guest")
    response = client.get(f"/api/v1/ws/negotiation?booking_id=1&token={token}")
    assert response.status_code == 403
