from celery import Celery
from app.config import settings

# Initialize Celery app
celery = Celery(
    "apnatask",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"]
)

# Celery configuration overrides
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

if __name__ == "__main__":
    celery.start()
