from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "ApnaTask Backend"
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgrespassword@db:5432/apnatask",
        description="Async PostgreSQL database URL for app"
    )
    SYNC_DATABASE_URL: str = Field(
        default="postgresql://postgres:postgrespassword@db:5432/apnatask",
        description="Sync PostgreSQL database URL (optional/alembic)"
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://redis:6379/0",
        description="Redis connection URL for location tracking and pub/sub"
    )

    # RabbitMQ / Celery
    CELERY_BROKER_URL: str = Field(
        default="amqp://guest:guest@rabbitmq:5672//",
        description="RabbitMQ Celery broker connection URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://redis:6379/1",
        description="Redis backend for Celery results"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
