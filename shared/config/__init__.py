"""
Configuration management using Pydantic Settings.
Loads configuration from environment variables.
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Service configuration
    service_name: str = "crypto-alert-engine"
    environment: str = "development"
    debug: bool = False
    
    # Redis configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # PostgreSQL configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "crypto_alerts"
    
    # Exchange API configuration
    binance_ws_url: str = "wss://stream.binance.com:9443/ws"
    bybit_ws_url: str = "wss://stream.bybit.com/v5/public/linear"
    
    # Rate limiting
    exchange_rate_limit: int = 20  # requests per second
    reconnect_delay: int = 5  # seconds
    max_reconnect_attempts: int = 10
    
    # Telegram configuration
    telegram_bot_token: Optional[str] = None
    
    # Email configuration (optional)
    sendgrid_api_key: Optional[str] = None
    email_from: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    
    @property
    def redis_url(self) -> str:
        """Build Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def postgres_url(self) -> str:
        """Build PostgreSQL connection URL."""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def postgres_url_sync(self) -> str:
        """Build PostgreSQL connection URL for sync operations."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
