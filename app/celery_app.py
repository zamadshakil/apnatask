from celery import Celery
from app.config import settings

celery_app = Celery(
    "apnatask",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Short time limits for hyperlocal task constraints
    task_time_limit=180,  # 3 minutes maximum runtime
    task_soft_time_limit=120,
)
