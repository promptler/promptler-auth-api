"""
Pydantic schemas for request/response validation
"""
from app.schemas.auth import (
    DeviceProfile,
    AppleSignInRequest,
    AppleSignInResponse,
    DeviceUpdateRequest,
    DeviceUpdateResponse
)

__all__ = [
    "DeviceProfile",
    "AppleSignInRequest",
    "AppleSignInResponse",
    "DeviceUpdateRequest",
    "DeviceUpdateResponse"
]
