"""
Apple Sign-In token verification using Apple's JWKS
"""
import time
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    InvalidTokenError,
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError
)
from fastapi import HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)


class AppleJWKSClient:
    """
    Singleton client for Apple JWKS with caching
    """
    _instance: Optional["AppleJWKSClient"] = None
    _jwks_client: Optional[PyJWKClient] = None
    _last_refresh: Optional[float] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._jwks_client is None:
            self._init_client()

    def _init_client(self):
        """Initialize the JWKS client"""
        self._jwks_client = PyJWKClient(
            settings.APPLE_JWKS_URL,
            cache_keys=True,
            max_cached_keys=10,
            cache_jwk_set=True,
            lifespan=settings.APPLE_JWKS_CACHE_TTL
        )
        self._last_refresh = time.time()
        logger.info(f"Initialized Apple JWKS client with URL: {settings.APPLE_JWKS_URL}")

    def get_signing_key(self, token: str):
        """Get the signing key for a token"""
        # Refresh client if cache is stale
        if self._last_refresh and (time.time() - self._last_refresh) > settings.APPLE_JWKS_CACHE_TTL:
            logger.info("JWKS cache expired, reinitializing client")
            self._init_client()

        return self._jwks_client.get_signing_key_from_jwt(token)


class AppleTokenVerifier:
    """
    Verifies Apple identity tokens against Apple's public keys
    """

    def __init__(self):
        self.jwks_client = AppleJWKSClient()

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify an Apple identity token and return the decoded payload

        Args:
            token: The JWT identity token from Apple Sign-In

        Returns:
            Dict containing the verified token payload

        Raises:
            HTTPException: If verification fails for any reason
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Identity token is required for verification"
            )

        try:
            # Get the signing key from Apple's JWKS
            signing_key = self.jwks_client.get_signing_key(token)

            # Verify and decode the token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.APPLE_BUNDLE_ID,
                issuer="https://appleid.apple.com",
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": ["exp", "iat", "sub", "aud", "iss"]
                }
            )

            logger.info(f"Successfully verified Apple token for user: {payload.get('sub')}")
            return payload

        except ExpiredSignatureError:
            logger.warning("Apple token verification failed: Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identity token has expired"
            )

        except InvalidAudienceError:
            logger.error(f"Apple token verification failed: Invalid audience (expected: {settings.APPLE_BUNDLE_ID})")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Identity token audience mismatch (expected bundle ID: {settings.APPLE_BUNDLE_ID})"
            )

        except InvalidIssuerError:
            logger.error("Apple token verification failed: Invalid issuer")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identity token issuer is not Apple"
            )

        except InvalidTokenError as e:
            logger.error(f"Apple token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid identity token: {str(e)}"
            )

        except Exception as e:
            logger.error(f"Unexpected error during Apple token verification: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify identity token"
            )

    def verify_and_extract_user_id(self, token: str) -> str:
        """
        Verify token and extract the Apple user ID (subject)

        Args:
            token: The JWT identity token from Apple Sign-In

        Returns:
            The Apple user identifier (sub claim)

        Raises:
            HTTPException: If verification fails or user ID is missing
        """
        payload = self.verify_token(token)

        user_id = payload.get("sub")
        if not user_id:
            logger.error("Apple token missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identity token is missing user identifier"
            )

        return user_id

    def extract_user_info(self, token: str) -> Dict[str, Any]:
        """
        Extract user information from the token payload

        Args:
            token: The JWT identity token from Apple Sign-In

        Returns:
            Dict with user information (email, email_verified, etc.)
        """
        payload = self.verify_token(token)

        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "email_verified": payload.get("email_verified", False),
            "is_private_email": payload.get("is_private_email", False),
            "issued_at": datetime.fromtimestamp(payload.get("iat", 0)),
            "expires_at": datetime.fromtimestamp(payload.get("exp", 0))
        }


# Singleton instance
apple_verifier = AppleTokenVerifier()
