import logging
from app.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.expire_booking")
def expire_booking(booking_id: int):
    logger.info(f"Checking expiration for booking {booking_id}")
    # In M4, this will inspect status in DB and transition to expired if still pending.
    return {"booking_id": booking_id, "status": "processed"}

@celery_app.task(name="app.tasks.send_push_notification")
def send_push_notification(user_id: int, message: str):
    logger.info(f"Sending push notification to user {user_id}: {message}")
    # Simulates sending a push notification by writing to standard output.
    print(f"PUSH_NOTIFICATION: User {user_id} -> {message}")
    return {"user_id": user_id, "sent": True}
