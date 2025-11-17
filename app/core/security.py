"""
Security utilities for API authentication
"""
import logging
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security_scheme = HTTPBearer(
    scheme_name="Bearer Token",
    description="API key for authenticating requests from the iOS app"
)


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme)
) -> str:
    """
    Verify the API key from the Authorization header

    Args:
        credentials: HTTP authorization credentials

    Returns:
        The validated API key

    Raises:
        HTTPException: If the API key is invalid or missing
    """
    if not credentials:
        logger.warning("Request missing authorization credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    valid_keys = settings.api_keys_list

    if not valid_keys:
        logger.error("No API keys configured in environment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication not configured"
        )

    if token not in valid_keys:
        logger.warning(f"Invalid API key attempted: {token[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )

    logger.debug("API key validated successfully")
    return token


def get_rate_limit_key(identifier: str, api_key: str) -> str:
    """
    Generate a unique rate limit key combining user identifier and API key

    Args:
        identifier: User identifier (apple_user_id)
        api_key: Validated API key

    Returns:
        Rate limit key string
    """
    # Hash the API key to avoid exposing it in logs
    import hashlib
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:8]
    return f"{identifier}:{key_hash}"
