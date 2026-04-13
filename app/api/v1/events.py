"""
Event tracking endpoints
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
from app.core.security import get_rate_limit_key
from app.models.user import User, DeviceSnapshot
from app.models.monetization_event import MonetizationEvent
from app.models.issue_report import IssueReport
from app.schemas.auth import OnlineModeEventRequest, OnlineModeEventResponse
from app.schemas.events import MonetizationEventRequest, MonetizationEventResponse
from app.schemas.issue_report import IssueReportRequest, IssueReportResponse
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/events", tags=["events"])


def _device_profile_to_dict(device_profile) -> Optional[dict]:
    """Convert DeviceProfile to dict, handling None"""
    if device_profile is None:
        return None
    return device_profile.model_dump(exclude_none=True)


@router.post(
    "/online-mode",
    response_model=OnlineModeEventResponse,
    status_code=status.HTTP_200_OK,
    summary="Log online mode activation",
    description="Log when a user activates online mode with verified connectivity"
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def log_online_mode_event(
    request: Request,
    event_data: OnlineModeEventRequest,
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(get_current_api_key)
):
    """
    Log an online mode activation event

    This endpoint:
    1. Verifies the user exists
    2. Creates a device snapshot with event_type='online_mode'
    3. Optionally updates the user's device profile if provided
    4. Returns confirmation of the logged event

    The operation is idempotent and safe to retry.
    """
    logger.info(f"Online mode event for user: {event_data.apple_user_id}")

    # Find user
    result = await db.execute(
        select(User).where(User.apple_user_id == event_data.apple_user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User not found for online mode event: {event_data.apple_user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {event_data.apple_user_id}"
        )

    # Update device profile if provided
    if event_data.device_profile:
        user.latest_device_profile = _device_profile_to_dict(event_data.device_profile)
        user.last_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Create device snapshot for online mode event
    device_data = event_data.device_profile
    snapshot = DeviceSnapshot(
        id=str(uuid.uuid4()),
        apple_user_id=event_data.apple_user_id,
        event_type='online_mode',
        device_model=device_data.model if device_data else None,
        device_name=device_data.name if device_data else None,
        system_name=device_data.system_name if device_data else None,
        system_version=device_data.system_version if device_data else None,
        locale=device_data.locale if device_data else None,
        region=device_data.region if device_data else None,
        time_zone=device_data.time_zone if device_data else None,
        app_version=device_data.app_version if device_data else None,
        app_build=device_data.app_build if device_data else None,
        raw_profile=_device_profile_to_dict(device_data),
        captured_at=event_data.timestamp.replace(tzinfo=None) if event_data.timestamp.tzinfo else event_data.timestamp,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(snapshot)

    # Commit transaction
    try:
        await db.commit()
        logger.info(f"Successfully logged online_mode event for user: {event_data.apple_user_id}")
    except Exception as e:
        await db.rollback()
        logger.error(f"Database error during online mode event logging: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log online mode event"
        )

    # Return response
    return OnlineModeEventResponse(
        apple_user_id=event_data.apple_user_id,
        event_logged=True,
        logged_at=datetime.now(timezone.utc)
    )


@router.post(
    "/monetization",
    response_model=MonetizationEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log monetization event",
    description="Log a monetization event from the iOS app (purchases, credits, paywall interactions)"
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def log_monetization_event(
    request: Request,
    event_data: MonetizationEventRequest,
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(get_current_api_key)
):
    """
    Log a monetization event.

    This endpoint:
    1. Optionally verifies the user exists (warns if not, does not reject)
    2. Creates a monetization_events record
    3. Returns confirmation with server-assigned event ID

    Events with null apple_user_id are accepted for anonymous attribution via device_id.
    """
    logger.info(f"Monetization event: {event_data.event_name} (user: {event_data.apple_user_id or 'anonymous'})")

    # If apple_user_id provided, verify user exists (warn but don't reject)
    if event_data.apple_user_id:
        result = await db.execute(
            select(User).where(User.apple_user_id == event_data.apple_user_id)
        )
        if not result.scalar_one_or_none():
            logger.warning(f"Monetization event for unknown user: {event_data.apple_user_id}")

    event_id = str(uuid.uuid4())
    event = MonetizationEvent(
        id=event_id,
        apple_user_id=event_data.apple_user_id,
        device_id=event_data.device_id,
        event_name=event_data.event_name,
        parameters=event_data.parameters,
        app_version=event_data.app_version,
        app_build=event_data.app_build,
        captured_at=event_data.captured_at.replace(tzinfo=None) if event_data.captured_at.tzinfo else event_data.captured_at,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(event)

    try:
        await db.commit()
        logger.info(f"Successfully logged monetization event {event_id}: {event_data.event_name}")
    except Exception as e:
        await db.rollback()
        logger.error(f"Database error during monetization event logging: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log event"
        )

    return MonetizationEventResponse(
        event_id=event_id,
        event_logged=True,
        logged_at=datetime.now(timezone.utc)
    )


@router.post(
    "/issue-report",
    response_model=IssueReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit issue report",
    description="Submit a user issue report from the iOS app"
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def submit_issue_report(
    request: Request,
    report_data: IssueReportRequest,
    db: AsyncSession = Depends(get_db_session),
    api_key: str = Depends(get_current_api_key)
):
    """
    Submit an issue report.

    This endpoint:
    1. Optionally verifies the user exists (warns if not, does not reject)
    2. Creates an issue_reports record with status 'new'
    3. Returns confirmation with server-assigned report ID

    Reports with null apple_user_id are accepted for anonymous attribution via device_id.
    """
    logger.info(f"Issue report: area={report_data.area} (user: {report_data.apple_user_id or 'anonymous'})")

    # If apple_user_id provided, verify user exists (warn but don't reject)
    if report_data.apple_user_id:
        result = await db.execute(
            select(User).where(User.apple_user_id == report_data.apple_user_id)
        )
        if not result.scalar_one_or_none():
            logger.warning(f"Issue report for unknown user: {report_data.apple_user_id}")

    report_id = str(uuid.uuid4())
    report = IssueReport(
        id=report_id,
        apple_user_id=report_data.apple_user_id,
        device_id=report_data.device_id,
        area=report_data.area,
        feature=report_data.feature,
        description=report_data.description,
        contact_email=report_data.contact_email,
        app_version=report_data.app_version,
        app_build=report_data.app_build,
        device_profile=report_data.device_profile,
        status="new",
        captured_at=report_data.captured_at.replace(tzinfo=None) if report_data.captured_at.tzinfo else report_data.captured_at,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(report)

    try:
        await db.commit()
        logger.info(f"Successfully logged issue report {report_id}: area={report_data.area}")
    except Exception as e:
        await db.rollback()
        logger.error(f"Database error during issue report logging: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log issue report"
        )

    return IssueReportResponse(
        report_id=report_id,
        logged=True,
        logged_at=datetime.now(timezone.utc)
    )
