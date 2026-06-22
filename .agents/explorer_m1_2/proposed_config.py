from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "ApnaTask Backend"
    ENV: str = Field(default="development", validation_alias="ENV")
    DEBUG: bool = Field(default=True, validation_alias="DEBUG")

    # Database URLs
    # FastAPI app uses async pg driver (asyncpg)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/apnatask",
        validation_alias="DATABASE_URL"
    )
    # Alembic/Sync uses sync pg driver (psycopg2)
    DATABASE_SYNC_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/apnatask",
        validation_alias="DATABASE_SYNC_URL"
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL"
    )

    # RabbitMQ / Celery Broker
    RABBITMQ_URL: str = Field(
        default="amqp://guest:guest@localhost:5672//",
        validation_alias="RABBITMQ_URL"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
