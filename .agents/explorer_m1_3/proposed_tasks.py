import logging
from app.celery_app import celery_app
from app.database import SessionLocal

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.expire_booking")
def expire_booking(booking_id: int) -> dict:
    """
    Asynchronous task triggered when a booking request is created.
    Delays for 3 minutes, then checks status in DB.
    If status remains 'pending', updates it to 'expired' and triggers push notification.
    """
    logger.info(f"Checking expiration for booking {booking_id}")
    
    db = SessionLocal()
    try:
        # In M4, actual DB query and updates will be implemented.
        # For now, we mock the expiration check.
        # status = get_booking_status(db, booking_id)
        # if status == "pending":
        #     update_booking_status(db, booking_id, "expired")
        #     send_push_notification.delay(customer_id, "Your booking request has expired.")
        logger.info(f"Booking {booking_id} expiration process executed successfully.")
        return {"booking_id": booking_id, "status": "processed"}
    except Exception as e:
        logger.error(f"Error during booking expiration task for booking {booking_id}: {str(e)}")
        raise e
    finally:
        db.close()

@celery_app.task(name="app.tasks.send_push_notification")
def send_push_notification(user_id: int, message: str) -> dict:
    """
    Simulates sending a push notification to a user.
    Logs the outcome to stdout or mock delivery queue.
    """
    logger.info(f"Sending push notification to user {user_id}: '{message}'")
    # Simulation logic
    print(f"[PUSH NOTIFICATION] To: User {user_id} | Msg: {message}")
    return {"user_id": user_id, "delivered": True}
