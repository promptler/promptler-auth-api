"""
API dependencies for endpoints
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.database import get_db
from app.core.security import verify_api_key


async def get_current_api_key(api_key: str = Depends(verify_api_key)) -> str:
    """
    Dependency to get and verify the current API key
    """
    return api_key


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session
    """
    async for session in get_db():
        yield session
