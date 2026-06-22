import logging
from app.celery_app import celery

logger = logging.getLogger(__name__)

@celery.task(name="app.tasks.expire_booking")
def expire_booking(booking_id: int):
    """
    Placeholder task for expiring bookings after 3 minutes.
    """
    logger.info(f"Expiring booking task triggered for booking_id: {booking_id}")
    return {"booking_id": booking_id, "status": "expired"}

@celery.task(name="app.tasks.send_push_notification")
def send_push_notification(user_id: int, message: str):
    """
    Placeholder task for sending push notifications.
    """
    logger.info(f"Sending push notification to user {user_id}: {message}")
    return {"user_id": user_id, "status": "sent"}
