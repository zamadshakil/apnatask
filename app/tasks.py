import logging
from app.celery_app import celery_app
from app.database import SessionLocal, BookingModel, UserPushTokenModel
import httpx
from celery.exceptions import SoftTimeLimitExceeded, Retry
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.expire_booking", bind=True, max_retries=3, default_retry_delay=5)
def expire_booking(self, booking_id: int) -> dict:
    """
    Asynchronous task triggered when a booking request is created.
    Delays for 3 minutes, then checks status in DB.
    If status remains 'pending', updates it to 'expired' and triggers push notification.
    """
    logger.info(f"Checking expiration for booking {booking_id}")
            
    db = SessionLocal()
    try:
        booking = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
        if not booking:
            logger.warning(f"Booking {booking_id} not found in database.")
            return {"booking_id": booking_id, "status": "not_found"}
            
        if booking.status == "pending":
            booking.status = "expired"
            
            # If there was a locked escrow transaction, refund it
            if booking.transaction_id:
                from app.mock_integrations.payments import MockPaymentEscrow
                try:
                    MockPaymentEscrow.refund_escrow(booking.transaction_id)
                except Exception as pay_err:
                    logger.error(f"Failed to refund escrow on timeout: {pay_err}")
                    
            db.commit()
            logger.info(f"Booking {booking_id} has expired.")
            
            # Trigger push notification
            send_push_notification.delay(booking.customer_id, "customer", "Your booking request has expired.")
            return {"booking_id": booking_id, "status": "expired"}
        else:
            logger.warning(f"Booking {booking_id} is already processed with status: {booking.status}")
            return {"booking_id": booking_id, "status": "already_processed"}
            
    except SoftTimeLimitExceeded as e:
        logger.error(f"Soft time limit exceeded for booking {booking_id}")
        return {"booking_id": booking_id, "status": "soft_time_limit_exceeded"}
    except OperationalError as exc:
        logger.warning(f"Database lock exception during booking {booking_id}. Retrying...")
        raise self.retry(exc=exc)
    except Retry:
        raise
    except Exception as e:
        logger.error(f"Error during booking expiration task for booking {booking_id}: {str(e)}")
        raise e
    finally:
        db.close()

@celery_app.task(name="app.tasks.send_push_notification")
def send_push_notification(user_id: int, role: str, message: str) -> dict:
    """
    Sends a push notification to a user via Expo Push API if registered,
    otherwise falls back to logging.
    """
    if user_id <= 0:
        logger.error(f"Invalid user_id {user_id} for push notification")
        raise ValueError("user_id must be greater than 0")
        
    logger.info(f"Sending push notification to {role} {user_id}: '{message}'")
    print(f"[PUSH NOTIFICATION] To: {role} {user_id} | Msg: {message}")
    
    db = SessionLocal()
    push_token = None
    try:
        token_record = db.query(UserPushTokenModel).filter(
            UserPushTokenModel.user_id == user_id,
            UserPushTokenModel.role == role
        ).first()
        if token_record:
            push_token = token_record.push_token
    except Exception as e:
        logger.error(f"Error querying push token for {role} {user_id}: {e}")
    finally:
        db.close()
        
    if push_token:
        # Real Expo push notification API call
        expo_url = "https://exp.host/--/api/v2/push/send"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-encoding": "gzip, deflate"
        }
        payload = {
            "to": push_token,
            "sound": "default",
            "title": "ApnaTask Update",
            "body": message
        }
        try:
            response = httpx.post(expo_url, json=payload, headers=headers, timeout=5.0)
            if response.status_code == 200:
                logger.info(f"Expo push notification successfully sent to token: {push_token}")
                return {"user_id": user_id, "role": role, "delivered": True, "token": push_token, "expo_response": response.json()}
            else:
                logger.error(f"Expo push notification failed with status {response.status_code}: {response.text}")
                return {"user_id": user_id, "role": role, "delivered": False, "error": f"Expo status {response.status_code}"}
        except Exception as http_err:
            logger.error(f"HTTP error sending Expo push notification: {http_err}")
            return {"user_id": user_id, "role": role, "delivered": False, "error": str(http_err)}
            
    return {"user_id": user_id, "role": role, "delivered": False, "reason": "No registered push token"}

