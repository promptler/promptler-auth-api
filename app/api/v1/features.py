"""
Feature prioritization endpoints
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import get_current_api_key, get_db_session
from app.core.security import get_rate_limit_key
from app.models.user import User
from app.models.feature_prioritization import FeaturePrioritization
from app.schemas.features import FeaturePrioritizationRequest, FeaturePrioritizationResponse
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/features", tags=["features"])


@router.post(
    "/prioritize",
    response_model=FeaturePrioritizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Track feature prioritization request",
    description="Records user's prioritization of a feature under construction using PostgreSQL upsert"
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def prioritize_feature(
    request: Request,
    prioritization_data: FeaturePrioritizationRequest,
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(get_current_api_key)
):
    """
    Track a feature prioritization request from a user

    This endpoint:
    1. Verifies the user exists
    2. Uses PostgreSQL's INSERT ON CONFLICT DO UPDATE to:
       - Insert a new record with counter=1 if this is the first time
       - Increment the counter if the user has already prioritized this feature
    3. Returns the current counter value and creation status

    The operation is atomic and safe for concurrent requests.
    """
    logger.info(f"Feature prioritization: user={prioritization_data.apple_user_id}, feature={prioritization_data.feature_code}")

    # Verify user exists
    result = await db.execute(
        select(User).where(User.apple_user_id == prioritization_data.apple_user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User not found for feature prioritization: {prioritization_data.apple_user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {prioritization_data.apple_user_id}"
        )

    # Prepare the upsert statement using PostgreSQL's INSERT ON CONFLICT
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    new_id = str(uuid.uuid4())

    stmt = insert(FeaturePrioritization).values(
        id=new_id,
        apple_user_id=prioritization_data.apple_user_id,
        feature_code=prioritization_data.feature_code,
        counter=1,
        created_at=now,
        updated_at=now
    ).on_conflict_do_update(
        constraint='uq_user_feature',
        set_={
            'counter': FeaturePrioritization.counter + 1,
            'updated_at': now
        }
    ).returning(
        FeaturePrioritization.id,
        FeaturePrioritization.counter,
        FeaturePrioritization.created_at,
        FeaturePrioritization.updated_at
    )

    # Execute the upsert
    try:
        result = await db.execute(stmt)
        row = result.fetchone()
        await db.commit()

        # Determine if this was a new record (created_at == updated_at)
        was_created = row.created_at == row.updated_at

        logger.info(
            f"Feature prioritization recorded: user={prioritization_data.apple_user_id}, "
            f"feature={prioritization_data.feature_code}, counter={row.counter}, created={was_created}"
        )

        return FeaturePrioritizationResponse(
            apple_user_id=prioritization_data.apple_user_id,
            feature_code=prioritization_data.feature_code,
            counter=row.counter,
            created=was_created,
            updated_at=row.updated_at
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Database error during feature prioritization: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record feature prioritization"
        )
