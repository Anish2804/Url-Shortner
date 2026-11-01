"""Application configuration management using Pydantic Settings."""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Platform configuration settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # General
    ENVIRONMENT: str = Field(default="development", description="Environment mode: development, staging, production, test")
    APP_NAME: str = Field(default="LinkScale Platform", description="Application display name")
    API_V1_STR: str = Field(default="/api/v1", description="API v1 prefix")
    DEBUG: bool = Field(default=False, description="Debug mode")
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production-min-32-chars-long", description="Secret key for JWT and cryptography")
    BASE_URL: str = Field(default="http://localhost:8000", description="Base URL for shortened links")

    # CORS
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
        description="Allowed CORS origins",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./urlshortener.db",
        description="Async SQLAlchemy database connection string",
    )
    DATABASE_POOL_SIZE: int = Field(default=20, ge=1, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0, le=50)
    DATABASE_POOL_TIMEOUT: int = Field(default=30, ge=1)
    DATABASE_ECHO: bool = Field(default=False)

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = Field(default=50, ge=1)
    REDIS_TIMEOUT_SECONDS: float = Field(default=2.0, ge=0.1)
    REDIS_URL_CACHE_TTL_SECONDS: int = Field(default=86400, ge=60, description="1 day default TTL for active short URLs")
    REDIS_CACHE_NULL_TTL_SECONDS: int = Field(default=300, ge=10, description="5 min TTL for non-existent URLs (penetration defense)")
    REDIS_RATE_LIMIT_ENABLED: bool = Field(default=True)

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="localhost:9092")
    KAFKA_TOPIC_CLICKS: str = Field(default="url-click-events")
    KAFKA_TOPIC_DLQ: str = Field(default="url-click-events-dlq")
    KAFKA_CONSUMER_GROUP: str = Field(default="analytics-workers-group")
    KAFKA_BATCH_SIZE: int = Field(default=100, ge=1)
    KAFKA_BATCH_TIMEOUT_MS: int = Field(default=500, ge=50)
    KAFKA_PRODUCER_TIMEOUT_MS: int = Field(default=1500, ge=100)
    KAFKA_PRODUCER_FALLBACK_QUEUE_MAX: int = Field(default=5000, ge=100)

    # Authentication & Security
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=14, ge=1)
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=1)
    MAX_FAILED_LOGIN_ATTEMPTS: int = Field(default=5, ge=1)
    ACCOUNT_LOCKOUT_MINUTES: int = Field(default=15, ge=1)

    # Rate Limiting (Requests Per Minute)
    RATE_LIMIT_ANONYMOUS_RPM: int = Field(default=60, ge=1)
    RATE_LIMIT_AUTHENTICATED_RPM: int = Field(default=300, ge=1)
    RATE_LIMIT_REDIRECT_RPM: int = Field(default=1200, ge=1)

    # URL Safety & Anti-SSRF
    ALLOW_PRIVATE_IPS: bool = Field(default=False)
    ALLOWED_URL_SCHEMES: Union[List[str], str] = Field(default=["http", "https"])
    MAX_URL_LENGTH: int = Field(default=2048, ge=10)

    @field_validator("ALLOWED_URL_SCHEMES", mode="before")
    @classmethod
    def assemble_allowed_schemes(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [scheme.strip().lower() for scheme in v.split(",") if scheme.strip()]
        return [s.lower() for s in v]

    # Observability
    METRICS_ENABLED: bool = Field(default=True)
    OTEL_ENABLED: bool = Field(default=False)
    OTEL_SERVICE_NAME: str = Field(default="url-shortener-service")
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(default="http://localhost:4317")
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")


settings = Settings()
