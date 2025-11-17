"""
Application configuration and settings
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    DATABASE_URL: str
    SYNC_DATABASE_URL: str

    # API Security
    API_SECRET_KEY: str
    API_KEYS: str  # Comma-separated list

    # Apple Sign-In
    APPLE_BUNDLE_ID: str
    APPLE_TEAM_ID: str
    APPLE_JWKS_URL: str = "https://appleid.apple.com/auth/keys"
    APPLE_JWKS_CACHE_TTL: int = 3600

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 10
    RATE_LIMIT_PER_HOUR: int = 100

    # Application
    APP_ENV: str = "production"
    APP_DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    CORS_ORIGINS: str = ""

    # Optional Sentry
    SENTRY_DSN: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    @property
    def api_keys_list(self) -> List[str]:
        """Parse comma-separated API keys"""
        return [key.strip() for key in self.API_KEYS.split(",") if key.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins"""
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


# Global settings instance
settings = Settings()
