"""
Revokes a user's Sign in with Apple tokens when they delete their account.

Apple asks apps that offer Sign in with Apple to revoke the user's tokens on account
deletion (App Review 5.1.1(v)); that removes the app from the user's "Sign in with Apple"
list in their Apple ID settings.

The iOS app sends the one-time authorization code from a fresh Sign in with Apple prompt
(valid for 5 minutes, usable once). We swap it for a refresh token, which needs a client
secret signed with our Sign in with Apple key, then revoke that token.

Never log the code, the client secret or Apple's tokens.
"""
import base64
import logging
import time
from typing import Optional

import httpx
import jwt

from app.config import settings

logger = logging.getLogger(__name__)

APPLE_ISSUER = "https://appleid.apple.com"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_REVOKE_URL = "https://appleid.apple.com/auth/revoke"
CLIENT_SECRET_LIFETIME_SECONDS = 300


def is_configured() -> bool:
    return bool(settings.APPLE_SIWA_KEY_ID and settings.APPLE_SIWA_PRIVATE_KEY_B64)


def _private_key() -> str:
    """The .p8 file's contents. Stored base64-encoded so it fits in one env line."""
    return base64.b64decode(settings.APPLE_SIWA_PRIVATE_KEY_B64).decode("utf-8")


def client_secret(now: Optional[float] = None) -> str:
    """Short-lived ES256 JWT that identifies Promptler to Apple's token endpoints."""
    issued_at = int(now if now is not None else time.time())
    return jwt.encode(
        {
            "iss": settings.APPLE_TEAM_ID,
            "iat": issued_at,
            "exp": issued_at + CLIENT_SECRET_LIFETIME_SECONDS,
            "aud": APPLE_ISSUER,
            # Codes from the native app belong to the bundle ID, not a Services ID.
            "sub": settings.APPLE_BUNDLE_ID,
        },
        _private_key(),
        algorithm="ES256",
        headers={"kid": settings.APPLE_SIWA_KEY_ID},
    )


def _apple_error(response: httpx.Response) -> str:
    try:
        return str(response.json().get("error", ""))
    except Exception:
        return ""


async def revoke_with_authorization_code(
    code: str,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> bool:
    """
    Swaps `code` for the user's tokens and revokes them. Returns True when Apple
    confirmed the revocation. Never raises: account deletion must not fail because
    Apple is unreachable or the code expired.
    """
    if not is_configured():
        logger.warning("Apple token revocation skipped: APPLE_SIWA_KEY_ID / APPLE_SIWA_PRIVATE_KEY_B64 not set")
        return False

    try:
        secret = client_secret()
        async with httpx.AsyncClient(timeout=10, transport=transport) as client:
            exchange = await client.post(APPLE_TOKEN_URL, data={
                "client_id": settings.APPLE_BUNDLE_ID,
                "client_secret": secret,
                "code": code,
                "grant_type": "authorization_code",
            })
            if exchange.status_code != 200:
                logger.warning(
                    f"Apple token revocation: code exchange failed "
                    f"(HTTP {exchange.status_code} {_apple_error(exchange)})"
                )
                return False

            tokens = exchange.json()
            if tokens.get("refresh_token"):
                token, hint = tokens["refresh_token"], "refresh_token"
            elif tokens.get("access_token"):
                token, hint = tokens["access_token"], "access_token"
            else:
                logger.warning("Apple token revocation: code exchange returned no token")
                return False

            revoke = await client.post(APPLE_REVOKE_URL, data={
                "client_id": settings.APPLE_BUNDLE_ID,
                "client_secret": secret,
                "token": token,
                "token_type_hint": hint,
            })
            if revoke.status_code != 200:
                logger.warning(
                    f"Apple token revocation failed (HTTP {revoke.status_code} {_apple_error(revoke)})"
                )
                return False
    except Exception as e:
        logger.error(f"Apple token revocation error: {type(e).__name__}")
        return False

    logger.info("Apple tokens revoked")
    return True
