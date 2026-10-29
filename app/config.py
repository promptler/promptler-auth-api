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
    API_KEYS: str  # Comma-separated list. Shipped inside the iOS app, so not secret: list a new
                   # key next to the old one before an app release, drop the old one later.
    ADMIN_API_KEYS: str = ""  # Comma-separated, server-side only (never in an app build).
                              # Lets the operator edit or delete a user without their token.

    # Apple identity token on POST /auth/apple. Keep True in production: without it,
    # anyone holding the app key could create or overwrite any user's profile.
    REQUIRE_IDENTITY_TOKEN: bool = True

    # Firebase App Check (see app/core/app_check.py). Empty project number = not checked.
    APP_CHECK_PROJECT_NUMBER: str = ""
    APP_CHECK_APP_IDS: str = ""  # Comma-separated Firebase app IDs allowed; empty = any app in the project
    ENFORCE_APP_CHECK: bool = False  # False = log missing/invalid tokens only

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
    def app_check_app_ids_list(self) -> List[str]:
        """Parse comma-separated Firebase app IDs"""
        return [app_id.strip() for app_id in self.APP_CHECK_APP_IDS.split(",") if app_id.strip()]

    @property
    def admin_api_keys_list(self) -> List[str]:
        """Parse comma-separated admin API keys"""
        return [key.strip() for key in self.ADMIN_API_KEYS.split(",") if key.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins"""
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


# Global settings instance
settings = Settings()
