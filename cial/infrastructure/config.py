"""
CIAL Configuration Management
Uses Pydantic Settings for environment-based configuration
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    # Application
    APP_NAME: str = "CIAL"
    API_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS"
    )

    # Redis (Short-Term Memory)
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_PASSWORD: str = Field(default="", env="REDIS_PASSWORD")
    REDIS_MAX_CONNECTIONS: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")

    # PostgreSQL (Long-Term Memory)
    POSTGRES_HOST: str = Field(default="localhost", env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=5432, env="POSTGRES_PORT")
    POSTGRES_DB: str = Field(default="cial_ltm", env="POSTGRES_DB")
    POSTGRES_USER: str = Field(default="cial_user", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(default="cial_password", env="POSTGRES_PASSWORD")

    @property
    def postgres_url(self) -> str:
        """PostgreSQL connection URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def async_postgres_url(self) -> str:
        """Async PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Kafka (Event Stream)
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="localhost:9093", env="KAFKA_BOOTSTRAP_SERVERS")
    KAFKA_CONSUMER_GROUP: str = Field(default="cial-agents", env="KAFKA_CONSUMER_GROUP")
    KAFKA_AUTO_OFFSET_RESET: str = Field(default="earliest", env="KAFKA_AUTO_OFFSET_RESET")

    # Intelligence Stream Topics
    KAFKA_TOPIC_PRICE_CRITICAL: str = "price.critical"
    KAFKA_TOPIC_SENTIMENT_BREAKING: str = "sentiment.breaking"
    KAFKA_TOPIC_WHALE_MASSIVE: str = "whale.massive"
    KAFKA_TOPIC_TECHNICAL_SIGNALS: str = "technical.signals"
    KAFKA_TOPIC_REGULATORY_ALERTS: str = "regulatory.alerts"
    KAFKA_TOPIC_DEFI_EVENTS: str = "defi.events"

    # TimescaleDB (Optional)
    TIMESCALEDB_HOST: str = Field(default="localhost", env="TIMESCALEDB_HOST")
    TIMESCALEDB_PORT: int = Field(default=5433, env="TIMESCALEDB_PORT")
    TIMESCALEDB_DB: str = Field(default="cial_timeseries", env="TIMESCALEDB_DB")

    # Memory TTL Settings (in seconds)
    TTL_LIVE_PRICES: int = Field(default=86400, env="TTL_LIVE_PRICES")  # 24 hours
    TTL_ORDERBOOK: int = Field(default=3600, env="TTL_ORDERBOOK")  # 1 hour
    TTL_BREAKING_NEWS: int = Field(default=2592000, env="TTL_BREAKING_NEWS")  # 30 days
    TTL_SENTIMENT: int = Field(default=86400, env="TTL_SENTIMENT")  # 24 hours
    TTL_WHALE_MOVEMENTS: int = Field(default=604800, env="TTL_WHALE_MOVEMENTS")  # 7 days
    TTL_TECHNICAL_INDICATORS: int = Field(default=86400, env="TTL_TECHNICAL_INDICATORS")  # 24 hours

    # API Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_PERIOD: int = Field(default=60, env="RATE_LIMIT_PERIOD")  # seconds

    # External API Keys (Data Sources)
    COINGECKO_API_KEY: str = Field(default="", env="COINGECKO_API_KEY")
    COINMARKETCAP_API_KEY: str = Field(default="", env="COINMARKETCAP_API_KEY")
    NEWS_API_KEY: str = Field(default="", env="NEWS_API_KEY")
    TWITTER_API_KEY: str = Field(default="", env="TWITTER_API_KEY")
    TWITTER_API_SECRET: str = Field(default="", env="TWITTER_API_SECRET")
    ETHERSCAN_API_KEY: str = Field(default="", env="ETHERSCAN_API_KEY")
    WHALE_ALERT_API_KEY: str = Field(default="", env="WHALE_ALERT_API_KEY")

    # Security
    SECRET_KEY: str = Field(default="change-me-in-production", env="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, env="ACCESS_TOKEN_EXPIRE_MINUTES")  # 24 hours

    # Monitoring
    ENABLE_PROMETHEUS: bool = Field(default=True, env="ENABLE_PROMETHEUS")
    SENTRY_DSN: str = Field(default="", env="SENTRY_DSN")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Use lru_cache to create a singleton.
    """
    return Settings()


# Global settings instance
settings = get_settings()
