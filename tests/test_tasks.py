import pytest
import logging
from unittest.mock import patch
from celery.exceptions import SoftTimeLimitExceeded, Retry
from app.database import BookingModel, SessionLocal
from app.tasks import expire_booking, send_push_notification

# Tier 1 Tests: Async Queue

def test_f3_t1_expire_booking_trigger():
    """Call expire_booking task synchronously and check returned status dictionary."""
    db = SessionLocal()
    booking = BookingModel(customer_id=1, amount=100.0, status="pending")
    db.add(booking)
    db.commit()
    booking_id = booking.id
    db.close()

    result = expire_booking(booking_id)
    assert isinstance(result, dict)
    assert result["booking_id"] == booking_id
    assert result["status"] == "expired"

def test_f3_t1_expire_booking_pending():
    """Verify expire_booking updates a pending booking's status to expired."""
    db = SessionLocal()
    booking = BookingModel(customer_id=2, amount=150.0, status="pending")
    db.add(booking)
    db.commit()
    booking_id = booking.id
    db.close()

    expire_booking(booking_id)

    db = SessionLocal()
    updated = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    assert updated.status == "expired"
    db.close()

def test_f3_t1_expire_booking_accepted():
    """Verify expire_booking does NOT change an accepted booking's status."""
    db = SessionLocal()
    booking = BookingModel(customer_id=3, amount=200.0, status="accepted")
    db.add(booking)
    db.commit()
    booking_id = booking.id
    db.close()

    expire_booking(booking_id)

    db = SessionLocal()
    updated = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    assert updated.status == "accepted"
    db.close()

def test_f3_t1_send_push_notification_logging(capsys):
    """Run send_push_notification task, verify task output matches message."""
    send_push_notification(10, "customer", "Hello ApnaTask")
    captured = capsys.readouterr()
    assert "[PUSH NOTIFICATION] To: customer 10 | Msg: Hello ApnaTask" in captured.out

def test_f3_t1_expire_booking_calls_notification():
    """Run expire_booking and check that it schedules a push notification."""
    db = SessionLocal()
    booking = BookingModel(customer_id=45, amount=100.0, status="pending")
    db.add(booking)
    db.commit()
    booking_id = booking.id
    db.close()

    with patch("app.tasks.send_push_notification.delay") as mock_notification:
        expire_booking(booking_id)
        mock_notification.assert_called_once_with(45, "customer", "Your booking request has expired.")


# Tier 2 Tests: Boundary & Corner Cases

def test_f3_t2_expire_booking_nonexistent(caplog):
    """Run expire_booking on nonexistent booking, check database query exception is handled."""
    with caplog.at_level(logging.WARNING):
        result = expire_booking(99999)
        assert result["status"] == "not_found"
        assert "Booking 99999 not found" in caplog.text

def test_f3_t2_send_push_negative_id(caplog):
    """Call send_push_notification with user_id <= 0, check error logs/validation."""
    with pytest.raises(ValueError, match="user_id must be greater than 0"):
        send_push_notification(0, "customer", "Invalid User")
    
    with pytest.raises(ValueError, match="user_id must be greater than 0"):
        send_push_notification(-5, "customer", "Negative User")

def test_f3_t2_task_soft_time_limit():
    """Force Celery worker soft time limit exception and ensure it is trapped."""
    with patch("app.tasks.SessionLocal") as mock_session_cls:
        mock_db = mock_session_cls.return_value
        mock_db.query.side_effect = SoftTimeLimitExceeded()
        
        result = expire_booking(1)
        assert result["status"] == "soft_time_limit_exceeded"

def test_f3_t2_db_retry_on_failure():
    """Simulate database lock and check that Celery retries the task."""
    from sqlalchemy.exc import OperationalError
    
    with patch("app.tasks.SessionLocal") as mock_session_cls:
        mock_db = mock_session_cls.return_value
        mock_db.query.return_value.filter.return_value.first.side_effect = OperationalError("SELECT FOR UPDATE", {}, "deadlock")
        
        with patch("app.tasks.expire_booking.retry") as mock_retry:
            mock_retry.side_effect = Retry("retrying")
            
            with pytest.raises(Retry):
                expire_booking(123)
                
            mock_retry.assert_called_once()

def test_f3_t2_worker_log_capture(caplog):
    """Ensure logger outputs warning when booking status is already processed."""
    db = SessionLocal()
    booking = BookingModel(customer_id=1, amount=100.0, status="completed")
    db.add(booking)
    db.commit()
    booking_id = booking.id
    db.close()

    with caplog.at_level(logging.WARNING):
        expire_booking(booking_id)
        assert f"Booking {booking_id} is already processed with status: completed" in caplog.text

def test_push_token_registration_endpoint(client):
    """Test register_push_token endpoint upsert behavior."""
    # Register token for customer 45
    resp = client.post("/api/v1/push-token", json={
        "user_id": 45,
        "role": "customer",
        "push_token": "ExponentPushToken[customer45token]"
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Verify stored in DB
    db = SessionLocal()
    from app.database import UserPushTokenModel
    token_record = db.query(UserPushTokenModel).filter(
        UserPushTokenModel.user_id == 45,
        UserPushTokenModel.role == "customer"
    ).first()
    assert token_record is not None
    assert token_record.push_token == "ExponentPushToken[customer45token]"

    # Re-register same token for another user/role (updates it)
    resp2 = client.post("/api/v1/push-token", json={
        "user_id": 55,
        "role": "provider",
        "push_token": "ExponentPushToken[customer45token]"
    })
    assert resp2.status_code == 200
    
    # Verify updated in DB
    db.expire_all()
    updated_record = db.query(UserPushTokenModel).filter(
        UserPushTokenModel.push_token == "ExponentPushToken[customer45token]"
    ).first()
    assert updated_record.user_id == 55
    assert updated_record.role == "provider"
    db.close()

def test_send_push_notification_with_expo_api():
    """Test that send_push_notification makes real HTTP call to Expo server when token exists."""
    from app.database import UserPushTokenModel
    
    # Seed push token
    db = SessionLocal()
    token_record = UserPushTokenModel(
        user_id=12,
        role="customer",
        push_token="ExponentPushToken[test_token_123]"
    )
    db.add(token_record)
    db.commit()
    db.close()

    # Patch httpx.post to simulate successful Expo push API response
    with patch("httpx.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"status": "ok"}}
        mock_post.return_value = mock_response

        res = send_push_notification(12, "customer", "Test Message")
        
        assert res["delivered"] is True
        assert res["token"] == "ExponentPushToken[test_token_123]"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://exp.host/--/api/v2/push/send"
        assert kwargs["json"]["to"] == "ExponentPushToken[test_token_123]"
        assert kwargs["json"]["body"] == "Test Message"
