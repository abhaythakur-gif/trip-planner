"""
Configuration management for the travel planning system.
Loads settings from environment variables and provides centralized config access.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Configuration
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_provider: Literal["openai", "anthropic"] = "openai"
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4000

    # External APIs
    amadeus_api_key: str = ""
    amadeus_api_secret: str = ""
    serpapi_key: str = ""
    opentripmap_api_key: str = ""  # Free key from opentripmap.io (1000 req/day)
    foursquare_api_key: str = ""  # Free key from foursquare.com (99k calls/day)
    # Note: Weather (Open-Meteo) and Places (Overpass/Nominatim) require no API key
    # Note: Calendar integration not implemented - will use iCal/ICS export when added

    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # Cache TTL (seconds)
    cache_ttl_flights: int = 21600  # 6 hours
    cache_ttl_hotels: int = 43200   # 12 hours
    cache_ttl_weather: int = 10800  # 3 hours
    cache_ttl_places: int = 604800  # 7 days

    # System Configuration
    max_replan_attempts: int = 3
    max_workflow_timeout: int = 300  # 5 minutes
    min_buffer_percentage: float = 0.05  # 5%
    min_confidence_score: float = 70.0

    # API Configuration
    api_key_header: str = "X-API-Key"
    api_rate_limit: int = 5  # requests per minute

    # Logging
    log_level: str = "INFO"
    sentry_dsn: str = ""

    # Environment
    environment: Literal["development", "staging", "production"] = "development"

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


# Global settings instance
settings = Settings()
