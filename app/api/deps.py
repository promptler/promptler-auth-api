"""
API dependencies for endpoints
"""
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Header, HTTPException, status

from app.database import get_db
from app.config import settings
from app.core.app_check import app_check_passes
from app.core.security import is_admin_key, verify_api_key


async def get_current_api_key(
    api_key: str = Depends(verify_api_key),
    x_firebase_appcheck: Optional[str] = Header(None),
) -> str:
    """
    Dependency to get and verify the current API key, plus the caller's App Check
    token. Admin keys are server-side only, so they skip App Check.
    """
    if settings.APP_CHECK_PROJECT_NUMBER and not is_admin_key(api_key):
        if not app_check_passes(x_firebase_appcheck) and settings.ENFORCE_APP_CHECK:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="App verification failed"
            )
    return api_key


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session
    """
    async for session in get_db():
        yield session
