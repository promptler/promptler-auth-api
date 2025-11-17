"""
Apple Sign-In authentication endpoints
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import get_current_api_key, get_db_session
from app.core.apple_auth import apple_verifier
from app.core.security import get_rate_limit_key
from app.models.user import User, DeviceSnapshot
from app.schemas.auth import (
    AppleSignInRequest,
    AppleSignInResponse,
    DeviceUpdateRequest,
    DeviceUpdateResponse
)
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["authentication"])


def _device_profile_to_dict(device_profile) -> Optional[dict]:
    """Convert DeviceProfile to dict, handling None"""
    if device_profile is None:
        return None
    return device_profile.model_dump(exclude_none=True)


@router.post(
    "/apple",
    response_model=AppleSignInResponse,
    status_code=status.HTTP_200_OK,
    summary="Apple Sign-In",
    description="Create or update user profile from Apple Sign-In. Idempotent operation."
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def apple_sign_in(
    request: Request,
    sign_in_data: AppleSignInRequest,
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(get_current_api_key)
):
    """
    Handle Apple Sign-In authentication

    This endpoint:
    1. Verifies the Apple identity token (if provided)
    2. Creates or updates the user profile
    3. Logs device snapshot
    4. Returns the stored user data

    The operation is idempotent - calling it multiple times with the same
    identifier will update the existing profile rather than create duplicates.
    """
    logger.info(f"Apple Sign-In request for user: {sign_in_data.apple_user_id}")

    # Verify identity token if provided (REQUIRED for production security)
    if sign_in_data.identity_token:
        try:
            token_user_id = apple_verifier.verify_and_extract_user_id(sign_in_data.identity_token)

            # Ensure token user ID matches the provided user ID
            if token_user_id != sign_in_data.apple_user_id:
                logger.error(
                    f"Token user ID mismatch: token={token_user_id}, provided={sign_in_data.apple_user_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User identifier does not match identity token"
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to verify identity token"
            )
    else:
        logger.warning(
            f"No identity token provided for user {sign_in_data.apple_user_id}. "
            "This should only happen in development/testing!"
        )
        # In production, you might want to reject requests without tokens:
        # raise HTTPException(status_code=400, detail="Identity token required")

    # Check if user exists
    result = await db.execute(
        select(User).where(User.apple_user_id == sign_in_data.apple_user_id)
    )
    existing_user = result.scalar_one_or_none()

    created = False

    if existing_user:
        # Update existing user
        logger.info(f"Updating existing user: {sign_in_data.apple_user_id}")

        # Update name/email only if provided (Apple only sends these on first sign-in)
        if sign_in_data.display_name:
            existing_user.display_name = sign_in_data.display_name
        if sign_in_data.email:
            existing_user.email = sign_in_data.email

        # Update device profile
        if sign_in_data.device_profile:
            existing_user.latest_device_profile = _device_profile_to_dict(sign_in_data.device_profile)

        existing_user.last_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        user = existing_user

    else:
        # Create new user
        logger.info(f"Creating new user: {sign_in_data.apple_user_id}")
        created = True

        user = User(
            apple_user_id=sign_in_data.apple_user_id,
            display_name=sign_in_data.display_name,
            email=sign_in_data.email,
            latest_device_profile=_device_profile_to_dict(sign_in_data.device_profile),
            first_seen_at=datetime.now(timezone.utc).replace(tzinfo=None),
            last_updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(user)

    # Create device snapshot if device profile provided
    if sign_in_data.device_profile:
        device_data = sign_in_data.device_profile
        snapshot = DeviceSnapshot(
            id=str(uuid.uuid4()),
            apple_user_id=sign_in_data.apple_user_id,
            device_model=device_data.model,
            device_name=device_data.name,
            system_name=device_data.system_name,
            system_version=device_data.system_version,
            locale=device_data.locale,
            region=device_data.region,
            time_zone=device_data.time_zone,
            app_version=device_data.app_version,
            app_build=device_data.app_build,
            raw_profile=_device_profile_to_dict(device_data),
            captured_at=sign_in_data.timestamp.replace(tzinfo=None) if sign_in_data.timestamp.tzinfo else sign_in_data.timestamp,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(snapshot)
        logger.info(f"Created device snapshot for user: {sign_in_data.apple_user_id}")

    # Commit transaction
    try:
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback()
        logger.error(f"Database error during Apple Sign-In: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save user profile"
        )

    # Return response
    return AppleSignInResponse(
        apple_user_id=user.apple_user_id,
        display_name=user.display_name,
        email=user.email,
        latest_device_profile=user.latest_device_profile,
        first_seen_at=user.first_seen_at,
        last_updated_at=user.last_updated_at,
        created=created
    )


@router.patch(
    "/apple/{identifier}",
    response_model=DeviceUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Update device metadata",
    description="Update device and app metadata for an existing user"
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def update_device_metadata(
    request: Request,
    identifier: str,
    update_data: DeviceUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(get_current_api_key)
):
    """
    Update device and app metadata for an existing user

    This lightweight endpoint updates only the device profile without
    requiring full Apple Sign-In re-authentication. Use this when the
    app needs to refresh local metadata (e.g., after an app update).
    """
    logger.info(f"Device update request for user: {identifier}")

    # Find user
    result = await db.execute(
        select(User).where(User.apple_user_id == identifier)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User not found for device update: {identifier}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {identifier}"
        )

    # Update device profile
    user.latest_device_profile = _device_profile_to_dict(update_data.device_profile)
    user.last_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Create device snapshot
    device_data = update_data.device_profile
    snapshot = DeviceSnapshot(
        id=str(uuid.uuid4()),
        apple_user_id=identifier,
        device_model=device_data.model,
        device_name=device_data.name,
        system_name=device_data.system_name,
        system_version=device_data.system_version,
        locale=device_data.locale,
        region=device_data.region,
        time_zone=device_data.time_zone,
        app_version=device_data.app_version,
        app_build=device_data.app_build,
        raw_profile=_device_profile_to_dict(device_data),
        captured_at=update_data.timestamp.replace(tzinfo=None) if update_data.timestamp.tzinfo else update_data.timestamp,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(snapshot)

    # Commit transaction
    try:
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback()
        logger.error(f"Database error during device update: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update device metadata"
        )

    logger.info(f"Successfully updated device metadata for user: {identifier}")

    return DeviceUpdateResponse(
        apple_user_id=user.apple_user_id,
        latest_device_profile=user.latest_device_profile,
        last_updated_at=user.last_updated_at
    )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the authentication service is running"
)
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "service": "promptler-auth",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
