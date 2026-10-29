"""
Firebase App Check verification.

The Bearer key ships inside the iOS app, so anyone can copy it. An App Check
token is minted by Firebase only for a genuine install that passed App Attest
(or DeviceCheck), lives about an hour, and is signed by Google, so a copied key
without a fresh token proves nothing. The app sends it as `X-Firebase-AppCheck`.

Rollout: with ENFORCE_APP_CHECK off, missing or invalid tokens are logged and
let through (older app builds send none). Turn it on once most calls verify.
"""
import logging
from typing import Optional

import jwt
from jwt import PyJWKClient

from app.config import settings

logger = logging.getLogger(__name__)

JWKS_URL = "https://firebaseappcheck.googleapis.com/v1/jwks"

_jwks_client: Optional[PyJWKClient] = None


def _jwks() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(JWKS_URL, cache_jwk_set=True, lifespan=6 * 3600)
    return _jwks_client


def verify_app_check_token(token: str) -> str:
    """Returns the Firebase app ID the token was minted for, or raises jwt.InvalidTokenError."""
    project_number = settings.APP_CHECK_PROJECT_NUMBER
    header = jwt.get_unverified_header(token)
    if header.get("alg") != "RS256" or header.get("typ") != "JWT":
        raise jwt.InvalidTokenError("unexpected App Check token header")
    payload = jwt.decode(
        token,
        _jwks().get_signing_key_from_jwt(token).key,
        algorithms=["RS256"],
        audience=f"projects/{project_number}",
        issuer=f"https://firebaseappcheck.googleapis.com/{project_number}",
        options={"require": ["exp", "iat", "sub", "aud", "iss"]},
    )
    app_id = payload["sub"]
    allowed = settings.app_check_app_ids_list
    if allowed and app_id not in allowed:
        raise jwt.InvalidTokenError("App Check token is for another app")
    return app_id


def app_check_passes(token: Optional[str]) -> bool:
    """True when the token verifies. Never raises; failures are logged."""
    if not token:
        logger.warning("Request without App Check token")
        return False
    try:
        verify_app_check_token(token)
        return True
    except Exception as e:
        logger.warning(f"App Check token rejected: {type(e).__name__}")
        return False
