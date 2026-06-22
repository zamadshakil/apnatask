from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    APP_NAME: str = "ApnaTask Backend"
    APP_ENV: str = Field(default="development", validation_alias="APP_ENV")
    
    # Database Settings
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/apnatask",
        validation_alias="DATABASE_URL"
    )
    ASYNC_DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/apnatask",
        validation_alias="ASYNC_DATABASE_URL"
    )
    
    # Redis Settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL"
    )
    
    # Celery Settings
    CELERY_BROKER_URL: str = Field(
        default="amqp://guest:guest@localhost:5672//",
        validation_alias="CELERY_BROKER_URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/1",
        validation_alias="CELERY_RESULT_BACKEND"
    )
    
    # JWT Settings (for WebSocket mock JWT auth)
    JWT_SECRET_KEY: str = Field(
        default="super-secret-key-change-in-production",
        validation_alias="JWT_SECRET_KEY"
    )
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
