"""
CIAL Configuration Management
Uses Pydantic V2 Settings for environment-based configuration

Version: 2.0 - Migrated to Pydantic V2
Performance: 20-50% faster validation
"""

from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from infrastructure.logging_config import logger


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Migrated to Pydantic V2 for improved performance and type safety.

    Features:
    - Environment variable loading with .env file support
    - Type validation and conversion
    - Computed properties for derived values
    - Singleton pattern via lru_cache
    """

    # Application Settings
    APP_NAME: str = "CIAL"
    API_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", validation_alias="ENVIRONMENT")
    DEBUG: bool = Field(default=True, validation_alias="DEBUG")
    HOST: str = Field(default="0.0.0.0", validation_alias="HOST")  # nosec B104 - Binding to all interfaces is intentional for containerized deployment
    PORT: int = Field(default=8000, validation_alias="PORT", ge=1, le=65535)
    LOG_LEVEL: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # CORS Settings
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        validation_alias="ALLOWED_ORIGINS",
        description="Allowed CORS origins",
    )

    # Redis Configuration (Short-Term Memory)
    # Can use REDIS_URL (full connection string) or individual fields
    REDIS_URL: str | None = Field(default=None, validation_alias="REDIS_URL")
    REDIS_HOST: str = Field(default="localhost", validation_alias="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, validation_alias="REDIS_PORT", ge=1, le=65535)
    REDIS_DB: int = Field(default=0, validation_alias="REDIS_DB", ge=0, le=15)
    REDIS_PASSWORD: str = Field(default="", validation_alias="REDIS_PASSWORD")
    REDIS_MAX_CONNECTIONS: int = Field(
        default=50,
        validation_alias="REDIS_MAX_CONNECTIONS",
        ge=1,
        le=1000,
        description="Maximum Redis connection pool size",
    )

    # PostgreSQL Configuration (Long-Term Memory)
    # Can use DATABASE_URL (full connection string) or individual fields
    DATABASE_URL: str | None = Field(default=None, validation_alias="DATABASE_URL")
    POSTGRES_HOST: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=5432, validation_alias="POSTGRES_PORT", ge=1, le=65535)
    POSTGRES_DB: str = Field(default="cial_ltm", validation_alias="POSTGRES_DB")
    POSTGRES_USER: str = Field(default="cial_user", validation_alias="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(default="cial_password", validation_alias="POSTGRES_PASSWORD")

    @model_validator(mode="after")
    def parse_connection_urls(self) -> "Settings":  # noqa: C901
        """
        Parse REDIS_URL and DATABASE_URL if provided.

        This allows deployment platforms like Render to provide full connection
        strings which we parse into individual components.
        """
        # Parse REDIS_URL if provided
        if self.REDIS_URL:
            try:
                parsed = urlparse(self.REDIS_URL)
                if parsed.hostname:
                    self.REDIS_HOST = parsed.hostname
                if parsed.port:
                    self.REDIS_PORT = parsed.port
                if parsed.password:
                    self.REDIS_PASSWORD = parsed.password
                # Extract DB from path (e.g., /0, /1)
                if parsed.path and len(parsed.path) > 1:
                    db_str = parsed.path.lstrip("/")
                    if db_str.isdigit():
                        self.REDIS_DB = int(db_str)
            except Exception as e:
                # If parsing fails, keep defaults
                logger.warning(f"Failed to parse REDIS_URL: {e}")
                pass

        # Parse DATABASE_URL if provided
        if self.DATABASE_URL:
            try:
                # Handle postgres:// or postgresql:// schemes
                parsed = urlparse(self.DATABASE_URL)
                if parsed.hostname:
                    self.POSTGRES_HOST = parsed.hostname
                if parsed.port:
                    self.POSTGRES_PORT = parsed.port
                if parsed.username:
                    self.POSTGRES_USER = parsed.username
                if parsed.password:
                    self.POSTGRES_PASSWORD = parsed.password
                if parsed.path and len(parsed.path) > 1:
                    self.POSTGRES_DB = parsed.path.lstrip("/")
            except Exception as e:
                # If parsing fails, keep defaults
                logger.warning(f"Failed to parse DATABASE_URL: {e}")
                pass

        return self

    @computed_field  # Pydantic V2 computed field
    @property
    def postgres_url(self) -> str:
        """Synchronous PostgreSQL connection URL"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def async_postgres_url(self) -> str:
        """Asynchronous PostgreSQL connection URL (asyncpg driver)"""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Kafka Configuration (Event Stream)
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:9093", validation_alias="KAFKA_BOOTSTRAP_SERVERS"
    )
    KAFKA_CONSUMER_GROUP: str = Field(
        default="cial-agents", validation_alias="KAFKA_CONSUMER_GROUP"
    )
    KAFKA_AUTO_OFFSET_RESET: str = Field(
        default="earliest", validation_alias="KAFKA_AUTO_OFFSET_RESET"
    )

    # Kafka Topics (Intelligence Stream)
    KAFKA_TOPIC_PRICE_CRITICAL: str = "price.critical"
    KAFKA_TOPIC_SENTIMENT_BREAKING: str = "sentiment.breaking"
    KAFKA_TOPIC_WHALE_MASSIVE: str = "whale.massive"
    KAFKA_TOPIC_TECHNICAL_SIGNALS: str = "technical.signals"
    KAFKA_TOPIC_REGULATORY_ALERTS: str = "regulatory.alerts"
    KAFKA_TOPIC_DEFI_EVENTS: str = "defi.events"

    # TimescaleDB Configuration (Optional - Time-Series Database)
    TIMESCALEDB_HOST: str = Field(default="localhost", validation_alias="TIMESCALEDB_HOST")
    TIMESCALEDB_PORT: int = Field(default=5433, validation_alias="TIMESCALEDB_PORT", ge=1, le=65535)
    TIMESCALEDB_DB: str = Field(default="cial_timeseries", validation_alias="TIMESCALEDB_DB")

    # Memory TTL Settings (Time-To-Live in seconds)
    TTL_LIVE_PRICES: int = Field(
        default=86400,  # 24 hours
        validation_alias="TTL_LIVE_PRICES",
        ge=60,  # Minimum 1 minute
        description="TTL for live price data",
    )
    TTL_ORDERBOOK: int = Field(default=3600, validation_alias="TTL_ORDERBOOK", ge=60)  # 1 hour
    TTL_BREAKING_NEWS: int = Field(
        default=2592000, validation_alias="TTL_BREAKING_NEWS", ge=3600  # 30 days
    )
    TTL_SENTIMENT: int = Field(default=86400, validation_alias="TTL_SENTIMENT", ge=60)  # 24 hours
    TTL_WHALE_MOVEMENTS: int = Field(
        default=604800, validation_alias="TTL_WHALE_MOVEMENTS", ge=3600  # 7 days
    )
    TTL_TECHNICAL_INDICATORS: int = Field(
        default=86400, validation_alias="TTL_TECHNICAL_INDICATORS", ge=60  # 24 hours
    )

    # API Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(
        default=100,
        validation_alias="RATE_LIMIT_REQUESTS",
        ge=1,
        le=10000,
        description="Maximum requests per period",
    )
    RATE_LIMIT_PERIOD: int = Field(
        default=60, validation_alias="RATE_LIMIT_PERIOD", ge=1, le=3600  # seconds
    )

    # External API Keys (Data Source Connectors)
    COINGECKO_API_KEY: str = Field(default="", validation_alias="COINGECKO_API_KEY")
    COINMARKETCAP_API_KEY: str = Field(default="", validation_alias="COINMARKETCAP_API_KEY")
    NEWS_API_KEY: str = Field(default="", validation_alias="NEWS_API_KEY")
    TWITTER_API_KEY: str = Field(default="", validation_alias="TWITTER_API_KEY")
    TWITTER_API_SECRET: str = Field(default="", validation_alias="TWITTER_API_SECRET")
    ETHERSCAN_API_KEY: str = Field(default="", validation_alias="ETHERSCAN_API_KEY")
    WHALE_ALERT_API_KEY: str = Field(default="", validation_alias="WHALE_ALERT_API_KEY")

    # Security Configuration
    SECRET_KEY: str = Field(
        default="change-me-in-production-min32chars!!",  # 40 characters
        validation_alias="SECRET_KEY",
        min_length=32,
        description="Secret key for JWT token signing (min 32 characters)",
    )
    ALGORITHM: str = Field(default="HS256", validation_alias="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=1440,  # 24 hours
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
        ge=1,
        le=43200,  # Max 30 days
    )

    # Monitoring & Observability
    ENABLE_PROMETHEUS: bool = Field(default=True, validation_alias="ENABLE_PROMETHEUS")
    SENTRY_DSN: str = Field(default="", validation_alias="SENTRY_DSN")

    # Pydantic V2 Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        validate_assignment=True,  # Validate on assignment
        validate_default=True,  # Validate default values
        extra="ignore",  # Ignore extra fields
        frozen=False,  # Allow mutation (for runtime config updates)
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to create a singleton pattern for application settings.
    This ensures settings are loaded once and reused throughout the application.

    Returns:
        Settings: Application configuration singleton

    Example:
        >>> settings = get_settings()
        >>> print(settings.REDIS_HOST)
        'localhost'
    """
    return Settings()


# Global settings instance
# This is the primary way to access settings throughout the application
settings = get_settings()


# Helper function for testing (allows settings override)
def get_settings_override() -> Settings:
    """
    Create a new settings instance (useful for testing).

    This bypasses the lru_cache and creates a fresh instance,
    allowing tests to use different configurations.

    Returns:
        Settings: Fresh settings instance

    Example:
        >>> from unittest.mock import patch
        >>> test_settings = Settings(REDIS_HOST="test-redis")
        >>> with patch('config.get_settings', return_value=test_settings):
        ...     # Tests with custom settings
    """
    return Settings()
